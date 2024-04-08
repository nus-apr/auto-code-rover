inherited-members should support more than one class
**Is your feature request related to a problem? Please describe.**
I have two situations:
- A class inherits from multiple other classes. I want to document members from some of the base classes but ignore some of the base classes
- A module contains several class definitions that inherit from different classes that should all be ignored (e.g., classes that inherit from list or set or tuple). I want to ignore members from list, set, and tuple while documenting all other inherited members in classes in the module.

**Describe the solution you'd like**
The :inherited-members: option to automodule should accept a list of classes. If any of these classes are encountered as base classes when instantiating autoclass documentation, they should be ignored.

**Describe alternatives you've considered**
The alternative is to not use automodule, but instead manually enumerate several autoclass blocks for a module. This only addresses the second bullet in the problem description and not the first. It is also tedious for modules containing many class definitions.


