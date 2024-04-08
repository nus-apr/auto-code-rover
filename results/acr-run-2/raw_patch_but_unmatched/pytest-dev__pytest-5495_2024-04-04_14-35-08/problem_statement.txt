Confusing assertion rewriting message with byte strings
The comparison with assertion rewriting for byte strings is confusing: 
```
    def test_b():
>       assert b"" == b"42"
E       AssertionError: assert b'' == b'42'
E         Right contains more items, first extra item: 52
E         Full diff:
E         - b''
E         + b'42'
E         ?   ++
```

52 is the ASCII ordinal of "4" here.

It became clear to me when using another example:

```
    def test_b():
>       assert b"" == b"1"
E       AssertionError: assert b'' == b'1'
E         Right contains more items, first extra item: 49
E         Full diff:
E         - b''
E         + b'1'
E         ?   +
```

Not sure what should/could be done here.
