Product pretty print could be improved
This is what the pretty printing for `Product` looks like:

```
>>> pprint(Product(1, (n, 1, oo)))
  ∞
┬───┬
│   │ 1
│   │
n = 1
>>> pprint(Product(1/n, (n, 1, oo)))
   ∞
┬──────┬
│      │ 1
│      │ ─
│      │ n
│      │
 n = 1
>>> pprint(Product(1/n**2, (n, 1, oo)))
    ∞
┬────────┬
│        │ 1
│        │ ──
│        │  2
│        │ n
│        │
  n = 1
>>> pprint(Product(1, (n, 1, oo)), use_unicode=False)
  oo
_____
|   | 1
|   |
n = 1
>>> pprint(Product(1/n, (n, 1, oo)), use_unicode=False)
   oo
________
|      | 1
|      | -
|      | n
|      |
 n = 1
>>> pprint(Product(1/n**2, (n, 1, oo)), use_unicode=False)
    oo
__________
|        | 1
|        | --
|        |  2
|        | n
|        |
  n = 1
```

(if those don't look good in your browser copy paste them into the terminal)

This could be improved:

- Why is there always an empty line at the bottom of the ∏? Keeping everything below the horizontal line is good, but the bottom looks asymmetric, and it makes the ∏ bigger than it needs to be.

- The ∏ is too fat IMO. 

- It might look better if we extended the top bar. I'm unsure about this. 

Compare this

```
    ∞
─┬─────┬─
 │     │  1
 │     │  ──
 │     │   2
 │     │  n
  n = 1
```

That's still almost twice as wide as the equivalent Sum, but if you make it much skinnier it starts to look bad.

```
  ∞
 ____
 ╲
  ╲   1
   ╲  ──
   ╱   2
  ╱   n
 ╱
 ‾‾‾‾
n = 1
```
