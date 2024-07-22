from tempfile import mkstemp
        # (1) apply the patch to source code
        with app_utils.cd(self.project_path):
            apply_cmd = ["git", "apply", patch_file]
            cp = app_utils.run_command(apply_cmd, capture_output=False, text=True)
            if cp.returncode != 0:
                # patch application failed
                raise RuntimeError(f"Error applying patch: {cp.stderr}")
        # (2) run the modified program against the test suite
        log_and_print("[Validation] Applied patch. Going to run test suite.")
        _, log_file = mkstemp(suffix=".log", prefix="pyval-", text=True)
        tests_passed, msg = self._run_test_suite_for_correctness(log_file)

        # (3) revert the patch to source code
        with app_utils.cd(self.project_path):
            app_utils.repo_clean_changes()
        log_and_print(
            f"[Validation] Finishing. Result is {tests_passed}. Message: {msg}."
        )