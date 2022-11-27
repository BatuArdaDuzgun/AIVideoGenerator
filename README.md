# AIVideoGenerator

skyline.py is run to test the code.

The code crates a zoom out video of a given image. Also it can generate an image using a text promt from DALLE-2 or Midjourney. After the image is chosen, first it creates a text prompt of the image using "methexis-inc / img2prompt". Then it upscales the image using "Python Imaging Library" and creates the desired zoom out video using the upscaled image.

