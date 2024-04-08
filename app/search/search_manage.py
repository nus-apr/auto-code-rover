from typing import List, MutableMapping, Optional, Tuple

from app.search import search_utils
from app.search.search_utils import SearchResult

RESULT_SHOW_LIMIT = 3


class SearchManager(object):
    def __init__(self, project_path: str):
        self.project_path = project_path
        # list of all files ending with .py, which are likely not test files
        # These are all ABSOLUTE paths.
        self.all_py_files: List[str] = []

        # for file name in the indexes, assume they are absolute path
        # class name -> [(file_name, start_line, end_line)]
        self.class_index: MutableMapping[str, List[Tuple[str, int, int]]] = dict()

        # {class_name -> {func_name -> [(file_name, start_line, end_line)]}}
        # inner dict is a list, since we can have (1) overloading func names,
        # and (2) multiple classes with the same name, having the same method
        self.class_func_index: MutableMapping[
            str, MutableMapping[str, List[Tuple[str, int, int]]]
        ] = dict()

        # function name -> [(file_name, start_line, end_line)]
        self.function_index: MutableMapping[str, List[Tuple[str, int, int]]] = dict()
        self.__build_index()

    def __build_index(self):
        """
        With all source code of the project, build two indexes:
            1. From class name to (source file, start line, end line)
            2. From function name to (source file, start line, end line)
        Since there can be two classes/functions with the same name, the mapping
        value is a list of tuples.
        This is for fast lookup whenever we receive a query.
        """
        self.all_py_files = search_utils.get_all_py_files(self.project_path)

        for py_file in self.all_py_files:
            # print(py_file)
            # (1) build class index
            classes = search_utils.get_all_classes_in_file(py_file)
            # now put the class result in one file into the dict
            for c, start, end in classes:
                if c not in self.class_index:
                    self.class_index[c] = []
                self.class_index[c].append((py_file, start, end))

            # (2) build class-function index
            for c, _, _ in classes:
                class_funcs = search_utils.get_all_funcs_in_class_in_file(py_file, c)
                if c not in self.class_func_index:
                    self.class_func_index[c] = dict()
                for f, start, end in class_funcs:
                    if f not in self.class_func_index[c]:
                        self.class_func_index[c][f] = []
                    self.class_func_index[c][f].append((py_file, start, end))

            # (3) build (top-level) function index
            functions = search_utils.get_top_level_functions(py_file)
            for f, start, end in functions:
                if f not in self.function_index:
                    self.function_index[f] = []
                self.function_index[f].append((py_file, start, end))

    def file_line_to_class_and_func(
        self, file_path: str, line_no: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Given a file path and a line number, return the class and function name.
        If the line is not inside a class or function, return None.
        """
        # check whether this line is inside a class
        for class_name in self.class_func_index:
            func_dict = self.class_func_index[class_name]
            for func_name, func_info in func_dict.items():
                for file_name, start, end in func_info:
                    if file_name == file_path and start <= line_no <= end:
                        return class_name, func_name

        # not in any class; check whether this line is inside a top-level function
        for func_name in self.function_index:
            for file_name, start, end in self.function_index[func_name]:
                if file_name == file_path and start <= line_no <= end:
                    return None, func_name

        # this file-line is not recorded in any of the indexes
        return None, None

    def __search_func_in_class(
        self, function_name: str, class_name: str
    ) -> List[SearchResult]:
        """
        Search for the function name in the class.
        Args:
            function_name (str): Name of the function.
            class_name (str): Name of the class.
        Returns:
            The list of code snippets searched.
        """
        result: List[SearchResult] = []
        if class_name not in self.class_func_index:
            return result
        if function_name not in self.class_func_index[class_name]:
            return result
        for fname, start, end in self.class_func_index[class_name][function_name]:
            func_code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, class_name, function_name, func_code)
            result.append(res)
        return result

    def __search_func_in_all_classes(self, function_name: str) -> List[SearchResult]:
        """
        Search for the function name in all classes.
        Args:
            function_name (str): Name of the function.
        Returns:
            The list of code snippets searched.
        """
        result: List[SearchResult] = []
        for class_name in self.class_index:
            res = self.__search_func_in_class(function_name, class_name)
            result.extend(res)
        return result

    def __search_top_level_func(self, function_name: str) -> List[SearchResult]:
        """
        Search for top-level function name in the entire project.
        Args:
            function_name (str): Name of the function.
        Returns:
            The list of code snippets searched.
        """
        result: List[SearchResult] = []
        if function_name not in self.function_index:
            return result

        for fname, start, end in self.function_index[function_name]:
            func_code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, None, function_name, func_code)
            result.append(res)
        return result

    def __search_func_in_code_base(self, function_name: str) -> List[SearchResult]:
        """
        Search for this function, from both top-level and all class definitions.
        """
        result: List[SearchResult] = []  # list of (file_name, func_code)
        # (1) search in top level
        top_level_res = self.__search_top_level_func(function_name)
        class_res = self.__search_func_in_all_classes(function_name)
        result.extend(top_level_res)
        result.extend(class_res)
        return result

    ###############################
    ### Interfaces ################
    ###############################

    # not search API - for writing patch
    # if we are searching for only a class when writing patch, likely we do not have enough info
    # the result can be too long, so we just show the first two
    def get_class_full_snippet(self, class_name: str) -> Tuple[str, str, bool]:
        summary = f"Class {class_name} did not appear in the codebase."
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, summary, False
        # class name -> [(file_name, start_line, end_line)]
        search_res: List[SearchResult] = []
        for fname, start, end in self.class_index[class_name]:
            code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, class_name, None, code)
            search_res.append(res)

        if not search_res:
            return tool_result, summary, False

        # the good path
        # for all the searched result, append them and form the final result
        tool_result = (
            f"Found {len(search_res)} classes with name {class_name} in the codebase.\n"
        )
        summary = tool_result
        if len(search_res) > 2:
            tool_result += "Too many results, showing full code for 2 of them:\n"
        for idx, res in enumerate(search_res[:2]):
            res_str = res.to_tagged_str(self.project_path)
            tool_result += f"Search result {idx + 1}: {res_str}\n\n"
        return tool_result, summary, True

    def search_class(self, class_name: str) -> Tuple[str, str, bool]:
        # initialize them to error case
        summary = f"Class {class_name} did not appear in the codebase."
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, summary, False

        search_res: List[SearchResult] = []
        for fname, _, _ in self.class_index[class_name]:
            # there are some classes; we return their signatures
            code = search_utils.get_class_signature(fname, class_name)
            res = SearchResult(fname, class_name, None, code)
            search_res.append(res)

        if not search_res:
            # this should not happen, but just in case
            return tool_result, summary, False

        # the good path
        # for all the searched result, append them and form the final result
        tool_result = (
            f"Found {len(search_res)} classes with name {class_name} in the codebase.\n"
        )
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_result += "They appeared in the following files:\n"
            tool_result += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_result += f"Search result {idx + 1}: {res_str}\n\n"
        summary = f"The tool returned information about class `{class_name}`."
        return tool_result, summary, True

    def search_class_in_file(self, class_name, file_name: str) -> Tuple[str, str, bool]:
        # (1) check whether we can get the file
        candidate_py_abs_paths = [f for f in self.all_py_files if f.endswith(file_name)]
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # (2) search for this class in the entire code base (we do filtering later)
        if class_name not in self.class_index:
            tool_output = f"Could not find class {class_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # (3) class is there, check whether it exists in the file specified.
        search_res: List[SearchResult] = []
        for fname, start_line, end_line in self.class_index[class_name]:
            if fname in candidate_py_abs_paths:
                class_code = search_utils.get_code_snippets(fname, start_line, end_line)
                res = SearchResult(fname, class_name, None, class_code)
                search_res.append(res)

        if not search_res:
            tool_output = f"Could not find class {class_name} in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        # good path; we have result, now just form a response
        tool_output = f"Found {len(search_res)} classes with name {class_name} in file {file_name}.\n"
        summary = tool_output
        for idx, res in enumerate(search_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"Search result {idx + 1}: {res_str}\n\n"
        return tool_output, summary, True

    def search_method_in_file(
        self, method_name: str, file_name: str
    ) -> Tuple[str, str, bool]:
        # (1) check whether we can get the file
        # supports both when file_name is relative to project root, and when
        # it is just a short name
        candidate_py_abs_paths = [f for f in self.all_py_files if f.endswith(file_name)]
        # print(candidate_py_files)
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # (2) search for this method in the entire code base (we do filtering later)
        search_res: List[SearchResult] = self.__search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"The method {method_name} does not appear in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # (3) filter the search result => they need to be in one of the files!
        filtered_res: List[SearchResult] = []
        for res in search_res:
            if res.file_path in candidate_py_abs_paths:
                filtered_res.append(res)

        # (4) done with search, now prepare result
        if not filtered_res:
            tool_output = (
                f"There is no method with name `{method_name}` in file {file_name}."
            )
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(filtered_res)} methods with name `{method_name}` in file {file_name}.\n"
        summary = tool_output

        # when searching for a method in one file, it's rare that there are many candidates
        # so we do not trim the result
        for idx, res in enumerate(filtered_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"Search result {idx + 1}: {res_str}\n\n"
        return tool_output, summary, True

    def search_method_in_class(
        self, method_name: str, class_name: str
    ) -> Tuple[str, str, bool]:
        if class_name not in self.class_index:
            tool_output = f"Could not find class {class_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # has this class, check its methods
        search_res: List[SearchResult] = self.__search_func_in_class(
            method_name, class_name
        )
        if not search_res:
            tool_output = f"Could not find method {method_name} in class {class_name}`."
            summary = tool_output
            return tool_output, summary, False

        # found some methods, prepare the result
        tool_output = f"Found {len(search_res)} methods with name {method_name} in class {class_name}.\n"
        summary = tool_output

        # There can be multiple classes defined in multiple files, which contain the same method
        # still trim the result, just in case
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += f"Too many results, showing full code for {RESULT_SHOW_LIMIT} of them, and the rest just file names:\n"
        first_five = search_res[:RESULT_SHOW_LIMIT]
        rest = search_res[RESULT_SHOW_LIMIT:]
        for idx, res in enumerate(first_five):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"Search result {idx + 1}: {res_str}\n\n"
        # for the rest, collect the file names into a set
        tool_output += f"Other results are in these files:\n"
        tool_output += SearchResult.collapse_to_file_level(rest, self.project_path)
        return tool_output, summary, True

    def search_method(self, method_name: str) -> Tuple[str, str, bool]:
        """
        Search for a method in the entire codebase.
        """
        search_res: List[SearchResult] = self.__search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"Could not find method {method_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(search_res)} methods with name {method_name} in the codebase.\n"
        summary = tool_output

        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"Search result {idx + 1}: {res_str}\n\n"

        return tool_output, summary, True

    def search_code(self, code_str: str) -> Tuple[str, str, bool]:
        # attempt to search for this code string in all py files
        all_search_results: List[SearchResult] = []
        for file_path in self.all_py_files:
            searched_line_and_code: List[Tuple[int, str]] = (
                search_utils.get_code_region_containing_code(file_path, code_str)
            )
            if not searched_line_and_code:
                continue
            for searched in searched_line_and_code:
                line_no, code_region = searched
                # from line_no, check which function and class we are in
                class_name, func_name = self.file_line_to_class_and_func(
                    file_path, line_no
                )
                res = SearchResult(file_path, class_name, func_name, code_region)
                all_search_results.append(res)

        if not all_search_results:
            tool_output = f"Could not find code {code_str} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # good path
        tool_output = f"Found {len(all_search_results)} snippets containing `{code_str}` in the codebase.\n"
        summary = tool_output

        if len(all_search_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(
                all_search_results, self.project_path
            )
        else:
            for idx, res in enumerate(all_search_results):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"Search result {idx + 1}: {res_str}\n\n"
        return tool_output, summary, True

    def search_code_in_file(
        self, code_str: str, file_name: str
    ) -> Tuple[str, str, bool]:
        code_str = code_str.removesuffix(")")

        candidate_py_files = [f for f in self.all_py_files if f.endswith(file_name)]
        if not candidate_py_files:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        # start searching for code in the filtered files
        all_search_results: List[SearchResult] = []
        for file_path in candidate_py_files:
            searched_line_and_code: List[Tuple[int, str]] = (
                search_utils.get_code_region_containing_code(file_path, code_str)
            )
            if not searched_line_and_code:
                continue
            for searched in searched_line_and_code:
                line_no, code_region = searched
                # from line_no, check which function and class we are in
                class_name, func_name = self.file_line_to_class_and_func(
                    file_path, line_no
                )
                res = SearchResult(file_path, class_name, func_name, code_region)
                all_search_results.append(res)

        if not all_search_results:
            tool_output = f"Could not find code {code_str} in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        # good path
        # There can be a lot of results, from multiple files.
        tool_output = f"Found {len(all_search_results)} snippets with code {code_str} in file {file_name}.\n"
        summary = tool_output
        if len(all_search_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following methods:\n"
            tool_output += SearchResult.collapse_to_method_level(
                all_search_results, self.project_path
            )
        else:
            for idx, res in enumerate(all_search_results):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"Search result {idx + 1}: {res_str}\n\n"
        return tool_output, summary, True

    def retrieve_code_snippet(
        self, file_path: str, start_line: int, end_line: int
    ) -> str:
        return search_utils.get_code_snippets(file_path, start_line, end_line)
