Unroll the iterable for all/any calls to get better reports
Sometime I need to assert some predicate on all of an iterable, and for that the builtin functions `all`/`any` are great - but the failure messages aren't useful at all!
For example - the same test written in three ways:

- A generator expression
```sh                                                                                                                                                                                                                         
    def test_all_even():
        even_stevens = list(range(1,100,2))
>       assert all(is_even(number) for number in even_stevens)
E       assert False
E        +  where False = all(<generator object test_all_even.<locals>.<genexpr> at 0x101f82ed0>)
```
- A list comprehension
```sh
    def test_all_even():
        even_stevens = list(range(1,100,2))
>       assert all([is_even(number) for number in even_stevens])
E       assert False
E        +  where False = all([False, False, False, False, False, False, ...])
```
- A for loop
```sh
    def test_all_even():
        even_stevens = list(range(1,100,2))
        for number in even_stevens:
>           assert is_even(number)
E           assert False
E            +  where False = is_even(1)

test_all_any.py:7: AssertionError
```
The only one that gives a meaningful report is the for loop - but it's way more wordy, and `all` asserts don't translate to a for loop nicely (I'll have to write a `break` or a helper function - yuck)
I propose the assertion re-writer "unrolls" the iterator to the third form, and then uses the already existing reports.

- [x] Include a detailed description of the bug or suggestion
- [x] `pip list` of the virtual environment you are using
```
Package        Version
-------------- -------
atomicwrites   1.3.0  
attrs          19.1.0 
more-itertools 7.0.0  
pip            19.0.3 
pluggy         0.9.0  
py             1.8.0  
pytest         4.4.0  
setuptools     40.8.0 
six            1.12.0 
```
- [x] pytest and operating system versions
`platform darwin -- Python 3.7.3, pytest-4.4.0, py-1.8.0, pluggy-0.9.0`
- [x] Minimal example if possible

