# PyBuddhabrot

The buddhabrot is a fractal based on the Mandelbrot fractal. However, it does not render images by checking the convergence of the sequence z = z² + c; rather it keeps the sequence which escapes and increase the pixel corresponding to each point of the sequence. This process reveals a mandelbrot-like shape, but with a lot more complexity and beauty.

Here is a [link](http://superliminal.com/fractals/bbrot/bbrot.htm) to its discoverer page, for a more in-depth presentation.

This project is a short python program, which generates images of the buddhabrot fractal, like this one.
It uses multithreading to speed up the computation, and let the user choose a wide range of parameters to tweak the computation (more tweaks will be added later).

This project will also be completely be rewritten in C++ in some time, for better performances.

# How to use

The program creates a file called `buddhabrot.bin`, which saves the current status of the computation, so you can stop the program and resume it later.

When launching `buddhabrot_gui.py` for the first time, you are asked to enter some values:
  * Width : the width of images produced
  * Height : the height ofimages produced
  * Number of complex numbers : the number of random complex numbers to pick and compute the sequence
  * Number of iterations : the number of iterations of the sequence to compute
  * Top left corner : the complex number that will designate the top left corner of the image
  * Bottom right corner : same thing for the bottom right corner of the image
Those values are saved in the `buddhabrot.bin` file and cannot be changed later.
Then other values are asked:
  * Number of cpus to use : 0 will take all available cpus
  * Batch size : number of complexes computed by a single cpu core before adding the result of its computation to the global image stocked in ram.
  * Number of complexes before creating an image : Will create a new image each time a multiple of this nuber is reached.
Those values can be redefined each time you launch the program.

Be careful not to take too big values. If width and height are too big, the `buddhabrot.bin` file could be huge, and the ram required could exceed one gigabit (a compression system to reduce the size by a factor of 20x is in development).
To not exceed your ram capacity, do not use too big values for the number of iterations (10.000.000 uses around 100Mo per cpu core).

To stop the computation, press `Shift + S`. The program will stop all current batches and save the progress into the file.

If you want to reset the values of each pixel but keep the parameters, run the command `python buddhabrot_reset.py` and type `Yes`.
If you want to reset everything, just delete the `buddhabrot.bin` file.

Here is an example of image produced by the program.

![example](https://github.com/Clematrics/PyBuddhabrot/blob/master/buddhabrot.png)

It used the following parameters:
  * Width : 6000
  * Height : 6000
  * Number of complex numbers : 0 (it means unlimited)
  * Number of iterations : 10000000
  * Top left corner : -2.25+1.5j (recommended value to get all the buddhabrot)
  * Bottom right corner : 0.75-1.5j (recommended value to get all the buddhabrot)

The image was rendered after 3200000 sequences of complex numbers where computed.

# Requirements

This program requires:
  * Python 3.6+
  * [imageio](https://imageio.github.io/)
  * [numpy](https://www.numpy.org/)
  * [asciimatics](https://github.com/peterbrittain/asciimatics)

# Installation

There is nothing to install. Just run the command `python buddhabrot_gui.py`.

