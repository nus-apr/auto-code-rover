from collections import defaultdict, namedtuple
from collections.abc import MutableMapping

from app.search import search_utils
from app.search.search_utils import SearchResult
from app.search.search_utils import RAGEmbeddingManager  

LineRange = namedtuple("LineRange", ["start", "end"])

ClassIndexType = MutableMapping[str, list[tuple[str, LineRange]]]
ClassFuncIndexType = MutableMapping[
    str, MutableMapping[str, list[tuple[str, LineRange]]]
]
FuncIndexType = MutableMapping[str, list[tuple[str, LineRange]]]

RESULT_SHOW_LIMIT = 3


class SearchManager:
    def __init__(self, project_path: str):
        self.project_path = project_path
        # list of all .py files (absolute paths), ignoring tests or 3rd-party
        self.parsed_files: list[str] = []

        # Class name -> [(file_name, line_range)]
        self.class_index: ClassIndexType = {}

        # {class_name -> {func_name -> [(file_name, line_range)]}}
        self.class_func_index: ClassFuncIndexType = {}

        # function name -> [(file_name, line_range)]
        self.function_index: FuncIndexType = {}

        # vector-based embedding manager
        self.rag_manager = RAGEmbeddingManager()

        # build the lexical index and store code snippets in the RAG manager
        self._build_index()
        

    def _build_index(self):
        """
        With all source code in project_path, build:
          1) class_index
          2) class_func_index
          3) function_index
        Then store these code snippets in the RAGEmbeddingManager for semantic search.
        """
        (
            class_index,
            class_func_index,
            function_index,
            parsed_files,
        ) = self._build_python_index()

        self._update_indices(class_index, class_func_index, function_index, parsed_files)

        # Build embeddings for each method, class, and top-level function
        # (We treat each snippet as a document for RAG.)
        self._build_rag_index()
        
        
    def _build_rag_index(self):
        """
        Build a retrieval-augmented (semantic) index by embedding each snippet as a document.
        """
        # 1) For each class in class_index, store a doc in RAG manager.
        for c_name, all_locs in self.class_index.items():
            for (file_name, line_rng) in all_locs:
                code = search_utils.get_code_snippets(file_name, line_rng.start, line_rng.end)
                snippet_id = f"{file_name}:{c_name}"  # unique ID
                self.rag_manager.add_document(snippet_id, code)

        # 2) For each method in class_func_index, store a doc in RAG manager.
        for c_name, func_dict in self.class_func_index.items():
            for f_name, all_locs in func_dict.items():
                for (file_name, line_rng) in all_locs:
                    code = search_utils.get_code_snippets(file_name, line_rng.start, line_rng.end)
                    snippet_id = f"{file_name}:{c_name}.{f_name}"
                    self.rag_manager.add_document(snippet_id, code)

        # 3) For top-level functions
        for f_name, all_locs in self.function_index.items():
            for (file_name, line_rng) in all_locs:
                code = search_utils.get_code_snippets(file_name, line_rng.start, line_rng.end)
                snippet_id = f"{file_name}:{f_name}"
                self.rag_manager.add_document(snippet_id, code)

        # Now finalize the indexing (build embeddings)
        self.rag_manager.build_embeddings()
        
        
        
    def _update_indices(
        self,
        class_index: ClassIndexType,
        class_func_index: ClassFuncIndexType,
        function_index: FuncIndexType,
        parsed_files: list[str],
    ) -> None:
        self.class_index.update(class_index)
        for c, fdict in class_func_index.items():
            if c not in self.class_func_index:
                self.class_func_index[c] = defaultdict(list)
            for fn, locs in fdict.items():
                self.class_func_index[c][fn].extend(locs)

        for fn, locs in function_index.items():
            if fn not in self.function_index:
                self.function_index[fn] = []
            self.function_index[fn].extend(locs)

        self.parsed_files.extend(parsed_files)

    def _build_python_index(
        self,
    ) -> tuple[ClassIndexType, ClassFuncIndexType, FuncIndexType, list[str]]:
        class_index: ClassIndexType = defaultdict(list)
        class_func_index: ClassFuncIndexType = defaultdict(lambda: defaultdict(list))
        function_index: FuncIndexType = defaultdict(list)

        py_files = search_utils.find_python_files(self.project_path)
        parsed_py_files = []
        for py_file in py_files:
            file_info = search_utils.parse_python_file(py_file)
            if file_info is None:
                continue
            parsed_py_files.append(py_file)
            classes, class_to_funcs, top_level_funcs = file_info

            # build class index
            for c, start, end in classes:
                class_index[c].append((py_file, LineRange(start, end)))

            # build class->func index
            for c, class_funcs in class_to_funcs.items():
                for f, start, end in class_funcs:
                    class_func_index[c][f].append((py_file, LineRange(start, end)))

            # build top-level function index
            for f, start, end in top_level_funcs:
                function_index[f].append((py_file, LineRange(start, end)))

        return class_index, class_func_index, function_index, parsed_py_files


    def file_line_to_class_and_func(
        self, file_path: str, line_no: int
    ) -> tuple[str | None, str | None]:
        """
        Given a file path and a line number, return (class_name, func_name).
        """
        # check whether this line is inside a class method
        for class_name, func_dict in self.class_func_index.items():
            for func_name, locs in func_dict.items():
                for fpath, rng in locs:
                    if fpath == file_path and rng.start <= line_no <= rng.end:
                        return class_name, func_name

        # not in any class; check top-level function
        for func_name, locs in self.function_index.items():
            for fpath, rng in locs:
                if fpath == file_path and rng.start <= line_no <= rng.end:
                    return None, func_name

        return None, None

    def _search_func_in_class(
        self, function_name: str, class_name: str
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        if class_name not in self.class_func_index:
            return results
        if function_name not in self.class_func_index[class_name]:
            return results

        for fname, rng in self.class_func_index[class_name][function_name]:
            func_code = search_utils.get_code_snippets(fname, rng.start, rng.end)
            res = SearchResult(fname, class_name, function_name, func_code)
            results.append(res)
        return results

    def _search_func_in_all_classes(self, function_name: str) -> list[SearchResult]:
        """
        Search for the function name in all classes.
        Args:
            function_name (str): Name of the function.
        Returns:
            The list of code snippets searched.
        """
        result: list[SearchResult] = []
        for class_name in self.class_index:
            res = self._search_func_in_class(function_name, class_name)
            result.extend(res)
        return result

    def _search_top_level_func(self, function_name: str) -> list[SearchResult]:
        """
        Search for top-level function name in the entire project.
        Args:
            function_name (str): Name of the function.
        Returns:
            The list of code snippets searched.
        """
        results: list[SearchResult] = []
        if function_name not in self.function_index:
            return results
        for fname, rng in self.function_index[function_name]:
            func_code = search_utils.get_code_snippets(fname, rng.start, rng.end)
            res = SearchResult(fname, None, function_name, func_code)
            results.append(res)
        return results

    def _search_func_in_code_base(self, function_name: str) -> list[SearchResult]:
        """
        Search for this function, from both top-level and all class definitions.
        """
        results: list[SearchResult] = []
        results.extend(self._search_top_level_func(function_name))
        results.extend(self._search_func_in_all_classes(function_name))
        return results

    ###############################
    ### Interfaces ################
    ###############################
    def semantic_search_code(self, query: str, top_k: int = 3) -> tuple[str, str, bool]:
        """
        Perform a semantic RAG-based search over the entire codebase.
        Return top_k code snippets that best match the query semantically.
        """
        rag_results = self.rag_manager.semantic_search(query, top_k=top_k)
        if not rag_results:
            tool_output = f"No semantic matches found for '{query}'"
            summary = tool_output
            return tool_output, summary, False

        tool_output = (
            f"Semantic search results (top {min(len(rag_results), top_k)}) for '{query}':\n\n"
        )
        for i, (snippet_id, score, snippet_code) in enumerate(rag_results, start=1):
            tool_output += f"- Result #{i} (score={score:.4f}):\n"
            tool_output += f"  <snippet_id>{snippet_id}</snippet_id>\n"
            tool_output += f"<code>\n{snippet_code}\n</code>\n\n"
        summary = f"Semantic search found {len(rag_results)} relevant snippet(s) for '{query}'."
        return tool_output, summary, True


    # not search API - for writing patch
    # if we are searching for only a class when writing patch, likely we do not have enough info
    # the result can be too long, so we just show the first two
    def get_class_full_snippet(self, class_name: str) -> tuple[str, str, bool]:
        summary = f"Class {class_name} did not appear in the codebase."
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, summary, False

        search_res: list[SearchResult] = []
        for fname, rng in self.class_index[class_name]:
            code = search_utils.get_code_snippets(fname, rng.start, rng.end)
            res = SearchResult(fname, class_name, None, code)
            search_res.append(res)

        if not search_res:
            return tool_result, summary, False

        tool_result = f"Found {len(search_res)} classes with name {class_name} in the codebase:\n\n"
        summary = tool_result
        if len(search_res) > 2:
            tool_result += "Showing full code for 2 of them:\n"
        for idx, res in enumerate(search_res[:2]):
            res_str = res.to_tagged_str(self.project_path)
            tool_result += f"- Search result {idx + 1}:\n```\n{res_str}\n```"
        return tool_result, summary, True

    def search_class(self, class_name: str) -> tuple[str, str, bool]:
        summary = f"Class {class_name} did not appear in the codebase."
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, summary, False

        search_res: list[SearchResult] = []
        for fname, _ in self.class_index[class_name]:
            code = search_utils.get_class_signature(fname, class_name)
            res = SearchResult(fname, class_name, None, code)
            search_res.append(res)

        if not search_res:
            return tool_result, summary, False

        tool_result = f"Found {len(search_res)} classes with name {class_name} in the codebase:\n\n"
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_result += "They appeared in the following files:\n"
            tool_result += SearchResult.collapse_to_file_level(search_res, self.project_path)
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_result += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        summary = f"The tool returned information about class `{class_name}`."
        return tool_result, summary, True

    def search_class_in_file(self, class_name, file_name: str) -> tuple[str, str, bool]:
        candidate_py_abs_paths = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        if class_name not in self.class_index:
            tool_output = f"Could not find class {class_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        search_res: list[SearchResult] = []
        for fname, (start_line, end_line) in self.class_index[class_name]:
            if fname in candidate_py_abs_paths:
                class_code = search_utils.get_code_snippets(fname, start_line, end_line)
                res = SearchResult(fname, class_name, None, class_code)
                search_res.append(res)

        if not search_res:
            tool_output = f"Could not find class {class_name} in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(search_res)} classes with name {class_name} in file {file_name}:\n\n"
        summary = tool_output
        for idx, res in enumerate(search_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_method_in_file(
        self, method_name: str, file_name: str
    ) -> tuple[str, str, bool]:
        candidate_py_abs_paths = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        search_res: list[SearchResult] = self._search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"The method {method_name} does not appear in the codebase."
            summary = tool_output
            return tool_output, summary, False

        filtered_res: list[SearchResult] = [
            r for r in search_res if r.file_path in candidate_py_abs_paths
        ]

        if not filtered_res:
            tool_output = f"No method with name `{method_name}` in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(filtered_res)} methods with name `{method_name}` in file {file_name}:\n\n"
        summary = tool_output
        for idx, res in enumerate(filtered_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_method_in_class(
        self, method_name: str, class_name: str
    ) -> tuple[str, str, bool]:
        if class_name not in self.class_index:
            tool_output = f"Could not find class {class_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        search_res: list[SearchResult] = self._search_func_in_class(method_name, class_name)
        if not search_res:
            tool_output = f"Could not find method {method_name} in class {class_name}`."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(search_res)} methods with name {method_name} in class {class_name}:\n\n"
        summary = tool_output

        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += f"Too many results, showing full code for {RESULT_SHOW_LIMIT} of them:\n"
        first_few = search_res[:RESULT_SHOW_LIMIT]
        for idx, res in enumerate(first_few):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        if len(search_res) > RESULT_SHOW_LIMIT:
            rest = search_res[RESULT_SHOW_LIMIT:]
            tool_output += "Other results are in these files:\n"
            tool_output += SearchResult.collapse_to_file_level(rest, self.project_path)
        return tool_output, summary, True

    def search_method(self, method_name: str) -> tuple[str, str, bool]:
        search_res: list[SearchResult] = self._search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"Could not find method {method_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(search_res)} methods with name {method_name} in the codebase:\n\n"
        summary = tool_output
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(search_res, self.project_path)
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"

        return tool_output, summary, True

    def search_code(self, code_str: str) -> tuple[str, str, bool]:
        all_search_results: list[SearchResult] = []
        for file_path in self.parsed_files:
            line_and_code = search_utils.get_code_region_containing_code(file_path, code_str)
            if not line_and_code:
                continue
            for (line_no, code_region) in line_and_code:
                class_name, func_name = self.file_line_to_class_and_func(file_path, line_no)
                res = SearchResult(file_path, class_name, func_name, code_region)
                all_search_results.append(res)

        if not all_search_results:
            tool_output = f"Could not find code {code_str} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(all_search_results)} snippets containing `{code_str}`:\n\n"
        summary = tool_output
        if len(all_search_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(all_search_results, self.project_path)
        else:
            for idx, res in enumerate(all_search_results):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_code_in_file(self, code_str: str, file_name: str) -> tuple[str, str, bool]:
        code_str = code_str.removesuffix(")")

        candidate_py_files = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_files:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        all_search_results: list[SearchResult] = []
        for file_path in candidate_py_files:
            line_and_code = search_utils.get_code_region_containing_code(file_path, code_str)
            if not line_and_code:
                continue
            for (line_no, code_region) in line_and_code:
                class_name, func_name = self.file_line_to_class_and_func(file_path, line_no)
                res = SearchResult(file_path, class_name, func_name, code_region)
                all_search_results.append(res)

        if not all_search_results:
            tool_output = f"Could not find code {code_str} in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        tool_output = (
            f"Found {len(all_search_results)} snippets with code {code_str} in file {file_name}:\n\n"
        )
        summary = tool_output
        if len(all_search_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following methods:\n"
            tool_output += SearchResult.collapse_to_method_level(
                all_search_results, self.project_path
            )
        else:
            for idx, res in enumerate(all_search_results):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def retrieve_code_snippet(
        self, file_path: str, start_line: int, end_line: int
    ) -> str:
        return search_utils.get_code_snippets(file_path, start_line, end_line)
