import replicate
import openai
import mytoken
import os
import requests
import glob
import numpy as np
import pandas as pd
import moviepy.video.io.ImageSequenceClip
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

def generate_candidate_images(prompt, candidate_img_amount, filename, session_nr):
    # create/check a folders
    os.makedirs("candidate_images", exist_ok=True)
    response = openai.Image.create(prompt=prompt, n=candidate_img_amount, size="1024x1024")
    for idx, url in enumerate(response['data']):
        r = requests.get(url['url'], allow_redirects=True, stream=True)
        image = Image.open(r.raw)
        # save the original candidate image: image1_candidate1_1024px_original.png
        image.save("candidate_images/{}{}_candidate{}_{}px_original.png".format(filename, session_nr, idx+1, image.size[0]))
        print("candidate image file 'candidate_images/{}{}_candidate{}_{}px_original.png' written...".format(filename, session_nr, idx+1, image.size[0]))
    print("")
    return session_nr+1

def generate_candidate_maskedimages(prompt, candidate_img_amount, filename, session_nr, downscale_pct):
    # load and downscale the upscaled image below 1024px size according to user given %
    downscaled = Image.open("{}{}_{}px_upscaled.png".format(filename, session_nr-1, 4096)).resize((int(1024*(downscale_pct/100)), int(1024*(downscale_pct/100))))
    new_image = Image.new(mode="RGBA", size=(1024,1024))
    # you paste the original image (scaled down) on top of the new white image with full alpha layer on
    new_image.paste(downscaled, (int((1024/2)-(int(1024*(downscale_pct/100))/2)), int((1024/2)-(int(1024*(downscale_pct/100))/2))))
    new_image.save("{}{}_{}px_masked.png".format(filename, session_nr-1, 1024))
    print("masked image used for outpainting '{}{}_{}px_masked.png' written...".format(filename, session_nr-1, 1024))
    print("")
    # create/check a folders
    os.makedirs("candidate_images", exist_ok=True)
    response = openai.Image.create_edit(
        image=open("{}{}_{}px_masked.png".format(filename, session_nr-1, 1024), "rb"),
        mask=open("{}{}_{}px_masked.png".format(filename, session_nr-1, 1024), "rb"),
        prompt=prompt,
        n=candidate_img_amount,
        size="1024x1024")
    for idx, url in enumerate(response['data']):
        r = requests.get(url['url'], allow_redirects=True, stream=True)
        image = Image.open(r.raw)
        # save the original candidate image: image2_candidate1_1024px_original.png
        image.save("candidate_images/{}{}_candidate{}_{}px_original.png".format(filename, session_nr, idx+1, image.size[0]))
        print("candidate image file 'candidate_images/{}{}_candidate{}_{}px_original.png' written...".format(filename, session_nr, idx+1, image.size[0]))
    print("")
    return session_nr+1

def generate_prompt_from_image(filename, session_nr, prompt, prompt_df):
    # load image to prompt pre-trained model
    model = replicate.models.get("methexis-inc/img2prompt")
    # call the API and predict a result stored in output variable
    # this will take many seconds ~50sec to finish calculating
    print("Calculating image to prompt... 30 sec")
    output = model.predict(image=open("{}{}_{}px_origin.png".format(filename, session_nr-1, 1024), "rb"))
    #  removes any leading and trailing space characters
    result = output.strip()
    # store the original user input 'prompt' text as well as the image2prompt string to a text file: image1_prompt.txt
    open("{}{}_prompt.txt".format(filename, session_nr-1), 'w').write("User prompt:\n{}\nImage prompt:\n{}".format(prompt, result))
    print("image2prompt file '{}{}_prompt.txt' written...".format(filename, session_nr-1))
    # print the result to the console
    print("\tPrompt:\n", result, "\n")
    tmp = pd.DataFrame(data={'userPrompt': [prompt], 'imagePrompt': [result]})
    return pd.concat([prompt_df, tmp])

def enlarge_selected_image(filename, session_nr):
    ## upscale 
    # load/show image from disk (same image)
    print("Calculating image enlargement")
    # load original image
    image = Image.open("{}{}_{}px_origin.png".format(filename, session_nr-1, 1024))
    # upscale the image linearly
    image = image.resize((4096, 4096))
    # save the upscaled image: image1_4096px_upscaled.png
    image.save("{}{}_{}px_upscaled.png".format(filename, session_nr-1, image.size[0]))
    print("enlarged file for video '{}{}_{}px_upscaled.png' written...".format(filename, session_nr-1, image.size[0]))
    print("")

# edit mytoken.py with your API TOKEN
# example: REPLICATE_API_TOKEN = "f77b55967be209bc63a12038af9c09e0d3211996"
# here we load the OS variable with the python variable token API id
os.environ['REPLICATE_API_TOKEN']=mytoken.REPLICATE_API_TOKEN
os.environ['OPENAI_API_KEY']=mytoken.OPENAI_API_TOKEN
openai.api_key = os.getenv("OPENAI_API_KEY")
session_nr = 1
prompt_df = pd.DataFrame()

filename = str(input("Enter the 'filename' to save images to (ex: image): "))
candidate_img_amount = int(input("Enter the amount of candidate images to choose from (1..9) (ex: 4): "))
print("")

# ask the user for the fixed value 'downscale' percentage
downscale_pct = int(input("Enter downscale percentage(%) (ex: 33): "))

prompt = str(input("Enter the DALLE2 prompt to generate image (ex: a white siamese cat): "))

# generate and store candidate AI images using the prompt
session_nr = generate_candidate_images(prompt, candidate_img_amount, filename, session_nr)

selection = int(input("Enter which image candidate you want to keep (ex: 1): "))
image = Image.open("candidate_images/{}{}_candidate{}_1024px_original.png".format(filename, session_nr-1, selection))
print("candidate image file you chose to select 'candidate_images/{}{}_candidate{}_1024px_original.png'".format(filename, session_nr-1, selection))
print("")

# save the original image, include size: image1_1024px_origin.png
image.save("{}{}_{}px_origin.png".format(filename, session_nr-1, image.size[0]))
print("original file '{}{}_{}px_origin.png' written...".format(filename, session_nr-1, image.size[0]))
print("")

# generate the prompt from the selected image
prompt_df = generate_prompt_from_image(filename, session_nr, prompt, prompt_df)

# enlarge the selected image
enlarge_selected_image(filename, session_nr)

while True:
    prompt = str(input("Enter the DALLE2 prompt to generate image (no input to stop) (ex: a white siamese cat): "))
    if len(prompt) == 0:
        # when no input is given, STOP
        print(f'you chose to stop, starting video creation phase...')
        break
    else:
        # input is given, continue execution
        # generate and store new candidate AI images using the prompt
        session_nr = generate_candidate_maskedimages(prompt, candidate_img_amount, filename, session_nr, downscale_pct)

        selection = int(input("Enter which image candidate you want to keep (ex: 1): "))
        image = Image.open("candidate_images/{}{}_candidate{}_1024px_original.png".format(filename, session_nr-1, selection))
        print("candidate image file you chose to select 'candidate_images/{}{}_candidate{}_1024px_original.png'".format(filename, session_nr-1, selection))
        print("")

        # save the original image, include size: image2_1024px_origin.png
        image.save("{}{}_{}px_origin.png".format(filename, session_nr-1, image.size[0]))
        print("original file '{}{}_{}px_origin.png' written...".format(filename, session_nr-1, image.size[0]))
        print("")

        # generate the prompt from the selected image
        prompt_df = generate_prompt_from_image(filename, session_nr, prompt, prompt_df)

        # enlarge the selected image
        enlarge_selected_image(filename, session_nr)
        continue

### starting the video generation
# store the prompt text data DataFrame, without the index, utf-8 encoding, delimiter ','
prompt_df.to_csv("{}_prompt.csv".format(filename), encoding='utf-8', sep=',', index=False)
# get all upscaled images and sort by numeric value
upscaled_image_files = glob.glob(filename+"*_upscaled.png")
upscaled_image_files.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))

def leftside(imgsize, width):
    # how to calculate the distance from the left
    value = round((imgsize-width)/2)
    if value == 0:
        return value+1
    else:
        return value

def topside(imgsize, width, ratio):
    # how to calculate the distance from the top
    return round((imgsize-width*ratio)/2)

def rightside(imgsize, width):
    # how to calculate the distance from the left to outer side
    return round((imgsize+width)/2)

def downside(imgsize, width, ratio):
    # how to calculate the distance from the top to outer side
    return round((imgsize+width*ratio)/2)

def create_coordinates(width, imgsize, ratio):
    # calculate based on width value all 4 coordinates of the cropped out square
    coordinates = []
    coordinates.append(leftside(imgsize, width)-1)
    coordinates.append(topside(imgsize, width, ratio)-1)
    coordinates.append(rightside(imgsize, width)-1)
    coordinates.append(downside(imgsize, width, ratio)-1)
    # create a tuple format for the coordinate values
    return (coordinates[0], coordinates[1], coordinates[2], coordinates[3])

def calculate_width_values(imgsize, width, nr_of_crops):
    stepsize = (imgsize-width)/(nr_of_crops-1)
    return [int(np.ceil(x)) for x in np.arange(width, imgsize+1, stepsize)]

# parameters HD video 60 fps used for images crop and scale
pref_width = int(input("Enter the 'width'(px) of the video (ex: 1280): "))
pref_height = int(input("Enter the 'height'(px) of the video (ex: 720): "))
ratio  = pref_height/pref_width
width  = int(4096*(downscale_pct/100))
height = int(width*ratio)
fps = int(input("Enter the 'fps' of the video (ex: 30): "))
seconds_image = int(input("Enter the duration(sec) of each AI image on the screen (ex: 4): "))
imgsize = 4096
nr_of_crops = fps * seconds_image
image_folder = 'images'
video_name = str(input("Enter the video 'filename' with 'codec' of the video (ex: finalvideo.mp4): "))
speed = round(1/fps, 4)

# upscaled_image_files
for idx, upscaled_image in enumerate(upscaled_image_files):
    print("starting new batch of images")
    # load in the upscaled image one-at-a-time
    image = Image.open(upscaled_image)
    image_coordinates = []
    for w in calculate_width_values(imgsize, width, nr_of_crops):
        image_coordinates.append(create_coordinates(w, imgsize, ratio))
    # create/check a folder
    os.makedirs(image_folder, exist_ok=True)
    # create the images inside the folder
    for img_number in range(nr_of_crops):
        cropped_image = image.crop(image_coordinates[img_number])
        cropped_image.resize((pref_width, pref_height)).save(image_folder + "/movieImg_{}.png".format(img_number+(idx*nr_of_crops)))
        print("cropped and rescaled image 'movieImg_{}.png' written ({}x{}) - step {}/{}".format((img_number+(idx*nr_of_crops)), pref_width, pref_height, (img_number+1)+(nr_of_crops*idx), nr_of_crops*len(upscaled_image_files)))

# get all the generated images *.png from the <image/> folder, sorted by numeric value
image_files = glob.glob(image_folder + "/movieImg_*.png")
image_files.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
# fix transition point between 2 images by removing one cropped image at the beginning of the new image
# I keep the original cropped pictures, but just remove certain items in the list
droplist = [x for x in range(0, len(image_files)-1, nr_of_crops)][1:]
for index in sorted(droplist, reverse=True):
    del image_files[index]

def duration_values_generator(timeperimage, downscale_pct, image_files, idx):
    # calculate a List of the duration time for each picture in the video
    # based on the downscaled image percentage cutoff (ex 33%) the first 67% of the time get a short duration time
    # then the remaining pictures receive a slightly longer duration time, hence slowing down little by little to half
    # this is needed because the transition to a new image is a zoomed out new version thus doubling the panning out that needs to be compensated with slower time
    # in case of 3 images = 10 cropped images:[2 2 2 2 2 2 2 2 2 2] 9 cropped images:[4 4 4 4 4 4 3 3.33, 2.67 2] 9 cropped images:[4 4 4 4 4 4 3 3.33, 2.67 2]
    durations = []
    first = (len(image_files)+idx)/(idx+1)
    second = (len(image_files)-first)/idx
    durations.extend(np.around(np.linspace(start=timeperimage*1, stop=timeperimage, num=round(((100-downscale_pct)/100)*first), endpoint=False), 4).tolist())
    durations.extend(np.around(np.linspace(start=timeperimage*1, stop=timeperimage, num=round((downscale_pct/100)*first), endpoint=True), 4).tolist())
    for i in range(idx):
        durations.extend(np.around(np.linspace(start=timeperimage*2, stop=timeperimage, num=round(((100-downscale_pct)/100)*second), endpoint=False), 4).tolist())
        durations.extend(np.around(np.linspace(start=timeperimage*1, stop=timeperimage, num=round((downscale_pct/100)*second), endpoint=True), 4).tolist())
    # here we then return the timetable list of each cropped image waiting time according to this algorithm, taking downscale percentage value cutoff in mind
    return durations

# load all images into memory to build a movie, using the timetable (how long each image stay in frame)
durations = duration_values_generator(speed, downscale_pct, image_files, idx)
clip = moviepy.video.io.ImageSequenceClip.ImageSequenceClip(sequence=image_files, durations=durations)
# write the video file to disk
clip.write_videofile(video_name, fps=fps)