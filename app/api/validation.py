class Validator:
    def validate(self, patch_file: str) -> tuple[bool, str, str]:
        """
        Returns:
            - Whether this patch has made the test suite pass.
            - Error message when running the test suite.
            - Path of written log file.
        """
        raise NotImplementedError("Validator is an abstract base class")
