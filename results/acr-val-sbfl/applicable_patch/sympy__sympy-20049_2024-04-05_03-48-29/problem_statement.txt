Point.vel() should calculate the velocity if possible
If you specify the orientation of two reference frames and then ask for the angular velocity between the two reference frames the angular velocity will be calculated. But if you try to do the same thing with velocities, this doesn't work. See below:

```
In [1]: import sympy as sm                                                                               

In [2]: import sympy.physics.mechanics as me                                                             

In [3]: A = me.ReferenceFrame('A')                                                                       

In [5]: q = me.dynamicsymbols('q')                                                                       

In [6]: B = A.orientnew('B', 'Axis', (q, A.x))                                                           

In [7]: B.ang_vel_in(A)                                                                                  
Out[7]: q'*A.x

In [9]: P = me.Point('P')                                                                                

In [10]: Q = me.Point('Q')                                                                               

In [11]: r = q*A.x + 2*q*A.y                                                                             

In [12]: Q.set_pos(P, r)                                                                                 

In [13]: Q.vel(A)                                                                                        
---------------------------------------------------------------------------
ValueError                                Traceback (most recent call last)
<ipython-input-13-0fc8041904cc> in <module>
----> 1 Q.vel(A)

~/miniconda3/lib/python3.6/site-packages/sympy/physics/vector/point.py in vel(self, frame)
    453         if not (frame in self._vel_dict):
    454             raise ValueError('Velocity of point ' + self.name + ' has not been'
--> 455                              ' defined in ReferenceFrame ' + frame.name)
    456         return self._vel_dict[frame]
    457 

ValueError: Velocity of point Q has not been defined in ReferenceFrame A
```

The expected result of the `Q.vel(A)` should be:

```
In [14]: r.dt(A)                                                                                         
Out[14]: q'*A.x + 2*q'*A.y
```

I think that this is possible. Maybe there is a reason it isn't implemented. But we should try to implement it because it is confusing why this works for orientations and not positions.


