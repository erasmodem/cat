import subprocess
#import os, time
#standard value, framestep = 1/fps in nanoseconds
fps = 25.0
framestep = 40000000

class Process(subprocess.Popen):
    def __init__(self):
        self.cmd = ""
        self.pid=None
    def open(self):
        self(self.cmd)
    def close(self, caller):
        self.kill()

def hmsf_to_time(tc, string=False, nanos=False):
    f = float(tc.split('.')[1])
    s = int(tc.split('.')[0].split(':')[2])
    m = int(tc.split(':')[1])
    h = int(tc.split(':')[0])
    if string==False:
        if nanos is True:
            return 1000000000*((h*3600)+(m*60)+s+(f/fps))
        else:
            return (h*3600)+(m*60)+s+(f/fps)

def time_to_hmsf(t, nanos=False, string=True):
    if nanos:
        secs = float(t)/1000000000.0
    else:
        secs = float(t)
    s, f = divmod(secs, 1)
    f = round(f*fps)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    
    if string:
        return "%02d:%02d:%02d.%02d" % (h, m, s, f)
    else:
        return (int(h), int(m), int(s), int(f))

def s_to_frames(t, nanos=False):
    if nanos == False:
        return int(divmod(t*fps, 1)[0])
    else:
        return int(divmod((t/1000000000.0)*fps, 1)[0])

def frames_to_s(frames, nanos=True):
    if nanos == True:
        return (frames/fps)*1000000000.0
    else:
        return (frames/fps)
        
def audioFrames_to_s(frames, sampleRate=48000.0, hop=512.0, vector=False):
    ratio = hop/sampleRate
    if vector == False:
        return frames*ratio
    else:
        for i in range(0, len(frames)):
            frames[i] *=ratio
        return frames

#AGGIORNARE A NUOVE STRUTTURE DATI
def shoot_the_shot(vid_file):
    step = 1.0/fps
    w, h = self.get_size()
    ratio = h/w
    prop_h = "500x"+ str(int(round(500*ratio)))
    
    for frame in self.shots:
        subprocess.call(['ffmpeg', '-ss', str(frame), '-i', self.vid_file, '-t', '1', 
                        '-s', prop_h, '-f', 'image2', '/frames/frame%04d-IN.jpeg'])
        subprocess.call(['ffmpeg', '-ss', str(frame+step), '-i', self.vid_file, '-t', '1', 
                        '-s', '500x', prop_h, '-f', 'image2', '/frames/frame%04d-OUT.jpeg'])

def get_fps(movie):
    get_fps = subprocess.Popen(("ffprobe", "-v", "0", 
                        "-of", "compact=p=0", 
                        "-show_entries",
                        "stream=avg_frame_rate",
                        "-select_streams","v", 
                        movie),
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT)
    output = get_fps.stdout.read()
    return float(output.split('=')[1].split('/')[0])

def get_size(vid_file):
    proc = subprocess.Popen(("ffprobe",
                        "-of",
                        "compact=p=0",
                        "-show_entries",
                        "stream=width:stream=height",
                        "-select_streams","v", 
                        vid_file),
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT)
                        
    data = (proc.stdout.read()).split('\n')[29]
    w = int(data.split('|')[0].split('=')[1])
    h = int(data.split('|')[1].split('=')[1])
    return w, h
