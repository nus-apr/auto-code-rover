Fix duplicated *args and **kwargs with autodoc_typehints
Fix duplicated *args and **kwargs with autodoc_typehints

### Bugfix
- Bugfix

### Detail
Consider this
```python
class _ClassWithDocumentedInitAndStarArgs:
    """Class docstring."""

    def __init__(self, x: int, *args: int, **kwargs: int) -> None:
        """Init docstring.

        :param x: Some integer
        :param *args: Some integer
        :param **kwargs: Some integer
        """
```
when using the autodoc extension and the setting `autodoc_typehints = "description"`.

WIth sphinx 4.2.0, the current output is
```
Class docstring.

   Parameters:
      * **x** (*int*) --

      * **args** (*int*) --

      * **kwargs** (*int*) --

   Return type:
      None

   __init__(x, *args, **kwargs)

      Init docstring.

      Parameters:
         * **x** (*int*) -- Some integer

         * ***args** --

           Some integer

         * ****kwargs** --

           Some integer

         * **args** (*int*) --

         * **kwargs** (*int*) --

      Return type:
         None
```
where the *args and **kwargs are duplicated and incomplete.

The expected output is
```
  Class docstring.

   Parameters:
      * **x** (*int*) --

      * ***args** (*int*) --

      * ****kwargs** (*int*) --

   Return type:
      None

   __init__(x, *args, **kwargs)

      Init docstring.

      Parameters:
         * **x** (*int*) -- Some integer

         * ***args** (*int*) --

           Some integer

         * ****kwargs** (*int*) --

           Some integer

      Return type:
         None

```
