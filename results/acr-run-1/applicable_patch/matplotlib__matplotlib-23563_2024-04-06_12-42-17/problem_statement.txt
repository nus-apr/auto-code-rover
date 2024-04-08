[Bug]: 'Line3D' object has no attribute '_verts3d'
### Bug summary

I use matplotlib 3D to visualize some lines in 3D. When I first run the following code, the code can run right. But, if I give `x_s_0[n]` a numpy array, it will report the error 'input operand has more dimensions than allowed by the axis remapping'. The point is when next I give  `x_s_0[n]` and other variables an int number, the AttributeError: 'Line3D' object has no attribute '_verts3d' will appear and can not be fixed whatever I change the variables or delete them. The error can be only fixed when I restart the kernel of ipython console. I don't know why it happens, so I come here for help.

### Code for reproduction

```python
x_s_0 = np.array(['my int number list'])
x_e_0 = np.array(['my int number list'])
y_s_0 = np.array(['my int number list'])
y_e_0 = np.array(['my int number list'])
z_s_0 = np.array(['my int number list'])
z_e_0 = np.array(['my int number list'])

fig = plt.figure()
        ax = fig.gca(projection='3d')
        ax.view_init(elev=90, azim=0)
        ax.set_zlim3d(-10, 10)
        clr_list = 'r-'

        for n in range(np.size(z_s_0, axis=0)):
            ax.plot([int(x_s_0[n]), int(x_e_0[n])],
                    [int(y_s_0[n]), int(y_e_0[n])],
                    [int(z_s_0[n]), int(z_e_0[n])], clr_list)

        plt.xlabel('x')
        plt.ylabel('y')
        # ax.zlabel('z')
        plt.title('90-0')
        plt.show()
```


### Actual outcome

Traceback (most recent call last):
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/IPython/core/interactiveshell.py", line 3444, in run_code
    exec(code_obj, self.user_global_ns, self.user_ns)
  File "<ipython-input-80-e04907066a16>", line 20, in <module>
    plt.show()
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/pyplot.py", line 368, in show
    return _backend_mod.show(*args, **kwargs)
  File "/home/hanyaning/.pycharm_helpers/pycharm_matplotlib_backend/backend_interagg.py", line 29, in __call__
    manager.show(**kwargs)
  File "/home/hanyaning/.pycharm_helpers/pycharm_matplotlib_backend/backend_interagg.py", line 112, in show
    self.canvas.show()
  File "/home/hanyaning/.pycharm_helpers/pycharm_matplotlib_backend/backend_interagg.py", line 68, in show
    FigureCanvasAgg.draw(self)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/backends/backend_agg.py", line 436, in draw
    self.figure.draw(self.renderer)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/artist.py", line 73, in draw_wrapper
    result = draw(artist, renderer, *args, **kwargs)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/artist.py", line 50, in draw_wrapper
    return draw(artist, renderer)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/figure.py", line 2803, in draw
    mimage._draw_list_compositing_images(
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/image.py", line 132, in _draw_list_compositing_images
    a.draw(renderer)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/artist.py", line 50, in draw_wrapper
    return draw(artist, renderer)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/mpl_toolkits/mplot3d/axes3d.py", line 469, in draw
    super().draw(renderer)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/artist.py", line 50, in draw_wrapper
    return draw(artist, renderer)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/axes/_base.py", line 3082, in draw
    mimage._draw_list_compositing_images(
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/image.py", line 132, in _draw_list_compositing_images
    a.draw(renderer)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/matplotlib/artist.py", line 50, in draw_wrapper
    return draw(artist, renderer)
  File "/home/hanyaning/anaconda3/envs/SBeA/lib/python3.8/site-packages/mpl_toolkits/mplot3d/art3d.py", line 215, in draw
    xs3d, ys3d, zs3d = self._verts3d
AttributeError: 'Line3D' object has no attribute '_verts3d'

### Expected outcome

Some 3D lines

### Additional information

_No response_

### Operating system

Local: windows + pycharm, Remote: Ubuntu 20.04

### Matplotlib Version

3.5.0

### Matplotlib Backend

module://backend_interagg

### Python version

3.8.12

### Jupyter version

_No response_

### Installation

pip
