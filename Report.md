# CS202 STTCSE

**Date:** 16/10/2026

## Abstract

BalVibe Studio is a researcher-facing web application for creating short,
educational experiment videos for children. The project takes a researcher's
experiment instructions and guides them through a structured workflow:
storyline generation, script and dialogue preparation, translation, voiceover
generation, scene visuals, and final video composition. The system is designed
to keep the experiment task consistent across scenes while also producing
timing information that can be used for synchronising narration, subtitles,
visual stimuli, and animation.

This week's work focused on moving beyond the voiceover and timing-dataset
stage towards the final visual-video stage. The implementation now has a
working path for assigning scene images, generating motion keyframes, and
combining those frames with the generated voiceover into an MP4 video. The
current version is intentionally a testing and demonstration build: its
sample workflow works locally, while live Gemini image generation remains
prepared as a future provider integration.

## Contributions

### Work completed up to last week

By the end of last week, the project's agents had been implemented up to
voiceover generation. The workflow could accept researcher instructions,
generate a gamified storyline, create the associated script and dialogues,
translate the narration, and synthesise scene-wise and combined voiceover
audio. The application also created a timing-ready dataset containing scene
durations, start and end times, frame positions, and audio-file references.
Approval gates were kept between the major stages so that the researcher could
review and edit the storyline and script before the later stages were run.

This provided the base for the final phase of the project: video generation.
The next phase required three connected responsibilities:

1. A character-generation agent to maintain a consistent character and
   generate the character's pose or action for each scene.
2. A background/image-generation agent to create or assign the visual
   background and scene image corresponding to the story and experiment
   stimulus.
3. A clubbing/composition agent to combine the scene frames, visual overlays,
   subtitles, and voiceover into the final rendered video.

### Anirudh Mittal

My contribution this week was focused on testing and connecting the visual
generation and video-rendering part of BalVibe Studio.

#### Character generation test with Gemini

I first explored the possibility of generating a stagnant, consistent
character image using Gemini as a test phase. The purpose was to check whether
one character could be retained across multiple scenes while changing its pose
or action according to the narration. This is important because a children's
experiment video should not appear to change its main character randomly from
scene to scene.

The Gemini image provider has been separated from the local provider in the
application architecture. It receives the scene descriptions, character
name, setting, and generated visual prompt. During this week's testing,
however, the actual Gemini Imagen request was not enabled. This was
intentional because the image-generation API is a paid service and we did not
want the testing workflow to make uncontrolled API calls. The provider
interface is therefore ready for a future `GEMINI_API_KEY`-based integration,
but the current demonstration uses locally available sample assets.

#### Background and scene-image generation

For the working test path, the image-generation stage uses local sample
images. For each scene, the system builds a Gemini-ready prompt containing the
character, setting, character state, trial information, and a short portion
of the scene narration. The prompt is saved with the scene metadata so that
it can later be used with a live image-generation model.

The local provider then assigns a sample image to each scene and stores it
inside the run's media directory. If a sample image is not available, the
system creates a simple fallback slide containing the scene number, setting,
character, and character state. This made it possible to test the rest of the
pipeline without depending on an external provider. The generated scene
records include the image filename, image URL, provider name, and storage
path, which allows the frontend and video renderer to use the same metadata.

The image stage also produces motion keyframes. These keyframes allow the
video stage to show a controlled sequence of frames instead of displaying a
single completely static image for the whole duration. The motion engine
keeps the scene timeline and the generated visual sequence connected to the
voiceover timing dataset.

#### Frame clubbing and final video rendering

After the images and voiceover dataset are available, the composition stage
combines them into a single video. It first reads the scene start and end
times, calculates the required number of frames from the selected FPS, and
creates a Remotion-compatible composition descriptor. It then loads the
generated keyframes or scene images and selects the correct visual for each
time position.

During rendering, the system adds the scene indicator, timer, trial-phase
label where applicable, and a lower-third subtitle banner. The subtitle text
is taken from the translated narration or the original scene script, with
pause markers removed from the visible text while their timing remains
represented in the audio. OpenCV and Pillow are used to construct the
frames, and the bundled FFmpeg executable is used to combine the rendered
visual stream with the combined WAV voiceover. The result is stored as an MP4
file together with the composition JSON, so the rendered output can be
played in the browser and inspected later.

This completed the connection between the earlier voiceover work and the
final video stage: **scene data -> images/keyframes -> timed frames ->
subtitles and overlays -> voiceover muxing -> MP4 output**.

#### Hosted demonstration

The current demonstration version can be opened here:

**[BalVibe Studio live demonstration](https://rare-waves-deny.loca.lt)**

The same application is also available directly on the development machine
at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

The public link is a temporary tunnel to the locally hosted version of my
implementation, so it is available only while the local server and tunnel
are running. The workflow should be tested using the loaded sample. In this
version, the Gemini-style images are hardcoded or selected from local sample
assets for testing; they are not generated through the Gemini API because the
live image-generation model is priced. A permanent Render deployment can
enable the live provider later by implementing the Gemini request and
securely adding the API key as a server-side environment variable.

### A

#### Contribution


### B

#### Contribution


### C

#### Contribution
