Possible bug in io.fits related to D exponents
I came across the following code in ``fitsrec.py``:

```python
        # Replace exponent separator in floating point numbers
        if 'D' in format:
            output_field.replace(encode_ascii('E'), encode_ascii('D'))
```

I think this may be incorrect because as far as I can tell ``replace`` is not an in-place operation for ``chararray`` (it returns a copy). Commenting out this code doesn't cause any tests to fail so I think this code isn't being tested anyway.
