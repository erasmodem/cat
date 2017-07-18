from __future__ import print_function
import subprocess
import numpy as np
from skimage.feature import register_translation
from scipy.stats import entropy as shannon_entropy
from scipy.stats import pearsonr
import matplotlib.pyplot as plt
import cv2
from Info import *
from Util import *

class Movie ():
    def __init__(self):
        self.file = ''
        self.framecount = 0
        self.length = 0
        self.audio = ''
        self.n_shots = 0
        self.n_seqs = 0
        self.shots = []
        self.seqs = []
        self.minfo = Movie_info()
        self.finfo = File_info("")
        self.features = {}

    def extract_audio(self):
        fname,  fext = os.path.splitext(self.file)
        ext = '.wav'
        self.audio = fname + '_audio' + ext
        subprocess.call(['ffmpeg', '-i', self.file, '-acodec', 'copy', '-vn', self.audio])

class Shot ():
    def __init__(self, *arg):
        self.index = arg[0]
        self.startns = arg[1]
        self.start = time_to_hmsf(arg[1], nanos=True)
        self.endns = arg[2]
        self.end = time_to_hmsf(arg[2], nanos=True)
        self.lengthns = self.endns - self.startns
        self.length = time_to_hmsf(self.lengthns, nanos=True)
        self.notes = ''
        self.vid_features = {}
        self.aud_features = {}

class Sequence ():
    def __init__(self, *arg):
        self.index = arg[0]
        self.title = arg[1]
        self.start = arg[2]
        self.startns = hmsf_to_time(self.start, nanos=True)
        self.end = arg[3]
        self.endns = hmsf_to_time(self.end, nanos=True)
        self.durationns = self.endns - self.startns
        self.duration = time_to_hmsf(self.durationns, nanos=True)
        self.notes = arg[4]
        self.crowd_index = 0
        if len(arg[5]) > 0:
            self.shots = self.shot_in_seq(arg[5])
        self.features = {}

    #returns the shots included in the sequence and the indexes of first and last shot
    def shot_in_seq(self, shotlist):
        first_found = False
        last = len(shotlist)
        for index, shot in enumerate(shotlist):
            if first_found == False and shot.startns >= self.startns:
                if shot.startns == self.startns:
                    first = index
                else:
                    first = index - 1
                first_found = True
            if shot.endns >= self.endns:
                last = index - 1
                break
        return (shotlist[first:(last+1)], first, last)

    def get_crowd_index(self):
        people = 0
        n_shots = self.shots[2]-self.shots[1]
        for shot in self.shots[0]:
            people += shot.vid_features["Charachters"]
        self.features["Crowd Index"] = people/n_shots


class VideoAnalysis():

    def __init__(self):
        self.features = ["ASL", "Shot Lengths", "ASL10", "ASL20", "Seqence Lengths", "AvgShotNumberinSeq", 
                        "ASLinSeq", "MSL", "MSL/ASL", "Number of Shots", "Coefficient of Variation",
                        "SL Standard Deviation", "SL Range,Max,Min", "SL Dynamics", 
                        "Lognormal Test"]
        self.nested_features = ["Brightness","Contrast", "Saturation", "Color", "Crowd Index", 
                        "Shot Scale","Optical Entropy", "Pan Tilt", "Shots in sequences", 
                        "Charachters", "Shannon Entropy"]
        self.feat_type = [[2, 0, 0, 0, 0, 2, 0, 2, 2, 2, 2, 2, 2, 0,
                         3, 0, 0, 0, 1, 0, 3, 0, 1, 0, 0, 0], 
                        ['line', 'multi', 'scalar', 'mat']]
        self.options = [False]*len(self.features)
        self.movie = None
        self.shots = []
        self.seqs = []
        self.sls = []
        self.configured = False

    def set_options(self, caller, id):
        self.options[id] = not self.options[id]

    def extract_shots(self, select_thres=0.2, black_min_duration=0.1, black_pixel_thres=0.05):
        self.shots = []
        vid_file = self.movie.file
        liminf=10*framestep
        #"-" in vid_file or
        if  "[" in vid_file or "]" in vid_file:
            return []
        scene_p = subprocess.Popen(("ffprobe", 
                                    "-show_frames",
                                    "-of",
                                    "compact=p=0", 
                                    "-f",
                                    "lavfi",
                                    "movie=" + vid_file + 
                                    ",select=gt(scene\," + str(select_thres) + 
                                    "),blackdetect=d="+ str(black_min_duration) + 
                                    ":pix_th=" + str(black_pixel_thres)),
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)
        output = scene_p.stdout.read()
        #get timings and convert in nanosecond for Gst.Player compatibility
        shot_in = 0.0
        idx=1
        res = output.split('\n')[18:-1]
        for i, line in enumerate(res):
            if res[i][0] != 'm':
                continue
            shot_out = (float(line.split('|')[4].split('=')[1])*1000000000.0)-framestep
            if (shot_out-shot_in)<=liminf:
                continue
            self.shots.append(Shot(idx, shot_in, shot_out))
            idx+=1
            shot_in = shot_out + framestep
        self.configured = True
        return self.shots

    def get_timings(self):
        t = "Number of shots: "+ str(len(self.shots)) +"\nShot timings: \n\t"
        for i, el in enumerate(self.shots[0:-1], start=1):
            t = t + str(i)+') ' + time_to_hmsf(el.end, nanos=True) + '\n\t'
        return t

    def get_shot_lengths(self):
        self.sls = []
        for shot in self.shots:
            self.sls.append(shot.lengthns/1000000000)

    def shot_scale(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False:
            return
        fd = cv2.CascadeClassifier('Classifier/haarcascade_frontalface_default.xml')
        ff2 = cv2.CascadeClassifier('Classifier/haarcascade_frontalface_alt2.xml')
#        ff1 = cv2.CascadeClassifier('Classifier/haarcascade_frontalface_alt.xml')
        fp = cv2.CascadeClassifier('Classifier/haarcascade_profileface.xml')
        shot_classifier = [("VLS", 0.01, 0.06, 1), ("LS", 0.06, 0.12, 2), ("MLS", 0.12, 0.25, 3), 
            ("MS", 0.25, 0.35, 4), ("MCU", 0.35, 0.5, 5), ("CU", 0.5, 0.8, 6), ("BCU", 0.8, 1.1, 7)]
        vect = [fd, ff2, fp]

        video_capture = cv2.VideoCapture(self.movie.file)
        height = video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)

        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]

        for shot in area:
            print(str(shot.index)+"/"+str(len(area))+" Shots")
            search=True
            ratios, squares, num_char = [], [], []
            end = shot.endns/1000000.0
            video_capture.set(cv2.CAP_PROP_POS_MSEC, shot.startns/1000000.0)
            while video_capture.get(cv2.CAP_PROP_POS_MSEC) <= end:
                # Capture every two frames
                if search == True:
                    search = False
                else:
                    search = True
                    ret = video_capture.grab()
                    if ret is False:
                        break
                    else:
                        continue
                ret, frame = video_capture.read()
                if ret is False:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                for i, cc in enumerate(vect):
                    #default values 1.1, 3, (30,30)
                    faces = cc.detectMultiScale(
                        gray,
                        scaleFactor=1.5,
                        minNeighbors=4,
                        minSize=(10,10))
                    squares.append(faces)
                    for (x, y, w, h) in faces:
                        ratios.append((float(h))/height)
                num_char.append(self.people_in(squares))
                squares = []
            shot.vid_features["Charachters"] = round(np.amax(num_char)-np.std(num_char))
            if len(ratios)>10:
                ratio = np.median(ratios)
                for type in shot_classifier:
                    if ratio >= type[1]:
                        if ratio < type[2]:
                            shot.vid_features["Shot Scale"] = [type[3], type[0]]
                            break
            else:
               shot.vid_features["Shot Scale"] = [0, "NoFace"]
        if workarea == "seq":
            self.seqs[current_seq].get_crowd_index()
        video_capture.release()

    def people_in(self, squares):
        count = 0
        center = []
        ignore = []
        for el in squares:
            for (x, y, w, h) in el:
                radius = w*np.sqrt(2)
                center.append(([x+w/2, y+h/2], radius))
        overlap = np.array([False]*len(center))
        prev_overlap = overlap
        for c in center:
            if c not in ignore:
                count +=1
                for i, alt_c in enumerate(center):
                    overlap[i] = np.linalg.norm(np.subtract(c[0],alt_c[0]))<c[1]
                overlap_history = np.logical_or(overlap, prev_overlap)
                ignore = np.array(center)[overlap_history]
                prev_overlap = overlap_history
        return count

    def movement_in_shot(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False:
            return
        lk_params = dict( winSize  = (25, 25),
                  maxLevel = 2,
                  criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

        feature_params = dict( maxCorners = 500,
                       qualityLevel = 0.3,
                       minDistance = 6,
                       blockSize = 6 )
        track_len = 10
        detect_interval = 5
        tracks = []
        video_capture = cv2.VideoCapture(self.movie.file)
        frame_idx = 0
        mov_max = []
        mov, movs = [], []

        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]

        for shot in area:
            print(str(shot.index)+"/"+str(len(area))+" Shots")
            end = shot.endns/1000000.0
            video_capture.set(cv2.CAP_PROP_POS_MSEC, shot.startns/1000000.0)
            while video_capture.get(cv2.CAP_PROP_POS_MSEC) <= end:
                ret, frame = video_capture.read()
                if ret is False:
                    break
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if len(tracks) > 0:
                    img0, img1 = prev_gray, frame_gray
                    p0 = np.float32([tr[-1] for tr in tracks]).reshape(-1, 1, 2)
                    p1, st, err = cv2.calcOpticalFlowPyrLK(img0, img1, p0, None, **lk_params)
                    p0r, st, err = cv2.calcOpticalFlowPyrLK(img1, img0, p1, None, **lk_params)
                    d = abs(p0-p0r).reshape(-1, 2).max(-1)
                    good = d < 1
                    if good.all():
                        mov.append(np.amax(abs(p1-p0).reshape(-1, 2)))
                    new_tracks = []
                    for tr, (x, y), good_flag in zip(tracks, p1.reshape(-1, 2), good):
                        if not good_flag:
                            continue
                        tr.append((x, y))
                        if len(tr) > track_len:
                            del tr[0]
                        new_tracks.append(tr)
                    tracks = new_tracks

                if frame_idx % detect_interval == 0:
                    if len(mov)>0:
                        mov_max.append(np.amax(mov))
                        mov = []
#                    mask = np.zeros_like(frame_gray)
#                    mask[:] = 255
#                    for x, y in [np.int32(tr[-1]) for tr in tracks]:
#                        cv2.circle(mask, (x, y), 5, 0, -1)
#                    p = cv2.goodFeaturesToTrack(frame_gray, mask = mask, **feature_params)
                    p = cv2.goodFeaturesToTrack(frame_gray, **feature_params)
                    if p is not None:
                        for x, y in np.float32(p).reshape(-1, 2):
                            tracks.append([(x, y)])
                frame_idx += 1
                prev_gray = frame_gray
            opt_ent = np.mean(mov_max)
            shot.vid_features["Optical Entropy"] = opt_ent
            movs.append(opt_ent)

        if workarea == "seq":
            self.seqs[current_seq].features["Optical Entropy"] = np.mean(movs)

        video_capture.release()

    def camera_movement(self, workarea="full", current_shot=0, current_seq=0):
        #estimate pan and tilt with phase correlation
        if self.configured == False:
            return
        video_capture = cv2.VideoCapture(self.movie.file)
        movs = []
        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]

        for shot in area:
            print(str(shot.index)+"/"+str(len(area))+" Shots")
            pan_tilt = [0.0, 0.0]
            frames_in_shot = s_to_frames(shot.lengthns, nanos=True)
            normArr = np.array([frames_in_shot, frames_in_shot])
            end = shot.endns/1000000.0
            video_capture.set(cv2.CAP_PROP_POS_MSEC, shot.startns/1000000.0)
            ret, im1 = video_capture.read()
            frame1 = cv2.cvtColor(im1, cv2.COLOR_BGR2GRAY)
            while video_capture.get(cv2.CAP_PROP_POS_MSEC) <= end:
                ret, im2 = video_capture.read()
                if ret is False:
                    break
                frame2 = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)
                shift, error, diffphase = register_translation(frame1,frame2, 6)
                pan_tilt = np.add(pan_tilt, shift)
                frame1 = frame2
            pt = abs(np.divide(pan_tilt, normArr))
            shot.vid_features["Pan Tilt"] = pt[::-1]
            movs.append(pt[::-1])

        if workarea == "seq":
            self.seqs[current_seq].features["Pan Tilt"] = np.mean(movs)
        video_capture.release()

    def camera_angle():
        #TODO
        pass
    def camera_stability():
        #TODO
        pass
    def shannon_entropy(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False:
            return
        shan_entr = []
        video_capture = cv2.VideoCapture(self.movie.file)

        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]

        for shot in area:
            print(str(shot.index)+"/"+str(len(area))+" Shots")
            entr = []
            end = shot.endns/1000000.0
            video_capture.set(cv2.CAP_PROP_POS_MSEC, shot.startns/1000000.0)
            while video_capture.get(cv2.CAP_PROP_POS_MSEC) <= end:
                ret, frame = video_capture.read()
                if ret is False:
                    break
                fg = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                entr.append(shannon_entropy(fg.ravel(), base=10))
                val = np.mean(entr)
                if np.isinf(val):
                    val = 0
            shot.vid_features["Shannon Entropy"]  = val
        video_capture.release()

    def carachters_id():
        pass
    def frame_geometry():
        pass
    def contrast_brightness_saturation(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False:
            return
        video_capture = cv2.VideoCapture(self.movie.file)

        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]

        for shot in area:
            print(str(shot.index)+"/"+str(len(area))+" Shots")
            brightness, contrast, saturation1, saturation2 = [], [], [], []
            end = shot.endns/1000000.0
            video_capture.set(cv2.CAP_PROP_POS_MSEC, shot.startns/1000000.0)
            while video_capture.get(cv2.CAP_PROP_POS_MSEC) <= end:
                # Capture frame-by-frame
                ret, frame = video_capture.read()
                if ret is False:
                    break
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2Lab)
                lum = cv2.split(lab)[0]
                lum = np.array(lum, dtype=np.float32)
                a = cv2.split(lab)[1]
                a = np.array(a, dtype=np.float32)
                b = cv2.split(lab)[2]
                b = np.array(b, dtype=np.float32)
                brightness.append(np.median(lum))
                contrast.append(np.std(lum))
                chroma = cv2.magnitude(a,b)
                saturation1.append(np.mean(cv2.divide(chroma, lum)))
                saturation2.append(np.mean(cv2.divide(chroma, cv2.magnitude(chroma, lum))))
            shot.vid_features["Brightness"] = np.mean(brightness)
            shot.vid_features["Contrast"] = np.mean(contrast)
            shot.vid_features["Saturation"] = np.mean(saturation1)
        video_capture.release()

    def color_table(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False:
            return
        step = fps/5.0
        index = 0
        video_capture = cv2.VideoCapture(self.movie.file)

        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]

        for shot in area:
            print(str(shot.index)+"/"+str(len(area))+" Shots")
            blue, green, red = [], [], []
            end = shot.endns/1000000.0
            video_capture.set(cv2.CAP_PROP_POS_MSEC, shot.startns/1000000.0)
            while video_capture.get(cv2.CAP_PROP_POS_MSEC) <= end:
                if index % step != 0:
                    index +=1
                    video_capture.grab()
                    continue
                # Capture a frame every step
                ret, frame = video_capture.read()
                if ret is False:
                    break
                blue = np.mean(frame[:, :, 0])
                green = np.mean(frame[:, :, 1])
                red = np.mean(frame[:, :, 2])
            avg_b = np.mean(blue)
            avg_g = np.mean(green)
            avg_r = np.mean(red)
            shot.vid_features["Color"] = (avg_r, avg_g, avg_b)
        video_capture.release()

    def feature_extraction(self):
        if self.configured == False:
            return
        self.get_shot_lengths()
        for id, todo in enumerate(self.options):
            if todo:
                if id == 0:
                    self.movie.features[self.features[id]] = float(self.movie.length)/self.movie.n_shots
                    continue
                if id == 1:
                    self.movie.features[self.features[id]] = self.sls
                    continue
                if id == 2:
                    if len(self.shots) < 10:
                        continue
                    avg10 = []
                    for i in range(len(self.shots)):
                        if i<5 or i>=len(self.shots)-5:
                            avg10.append(0.0)
                        else:
                            avg10.append(np.mean(self.sls[i-5:i+5+1]))
                    self.movie.features[self.features[id]] = avg10
                    continue
                if id == 3:
                    if len(self.shots) < 20:
                        continue
                    avg20 = []
                    for i in range(len(self.shots)):
                        if i<10 or i>=len(self.shots)-10:
                            avg20.append(0.0)
                        else:
                            avg20.append(np.mean(self.sls[i-10:i+10+1]))
                    self.movie.features[self.features[id]] = avg20
                    continue
                if id == 4:
                    if len(self.seqs) == 0:
                        continue
                    seq_lengths = []
                    for seq in self.seqs:
                        seq_lengths.append(seq.durationns/1000000000)
                    self.movie.features[self.features[id]] = seq_lengths
                    continue
                if id == 5:
                    if len(self.seqs) == 0:
                        continue
                    sis = []
                    for seq in self.seqs:
                        sis.append(len(seq.shots[0]))
                    self.movie.features["Shots in sequences"] = sis
                    self.movie.features[self.features[id]] = np.mean(sis)
                    continue
                if id == 6:
                    if len(self.seqs) == 0:
                        continue
                    seq_asl = []
                    for seq in self.seqs:
                        seq_asl.append(np.mean(self.sls[seq.shots[1]:seq.shots[2]+1]))
                    self.movie.features[self.features[id]] = seq_asl
                    continue
                if id == 7:
                    self.movie.features[self.features[id]] = np.median(self.sls)
                    continue
                if id == 8:
                    ASL = float(self.movie.length)/self.movie.n_shots
                    MSL = np.median(self.sls)
                    self.movie.features[self.features[id]] = MSL/ASL
                    continue
                if id == 9:
                    self.movie.features[self.features[id]] = self.movie.n_shots
                    continue
                if id == 10:
                    ASL = float(self.movie.length)/self.movie.n_shots
                    stDev = np.std(self.sls)
                    self.movie.features[self.features[id]] = stDev/ASL
                    continue
                if id == 11:
                    self.movie.features[self.features[id]] = np.std(self.sls)
                    continue
                if id == 12:
                    max = np.amax(self.sls)
                    min = np.amin(self.sls)
                    self.movie.features[self.features[id]] = (max-min, max, min)
                    continue
                if id == 13:
                    dyn = []
                    prev = 0
                    for sl in self.sls:
                        dyn.append(sl-prev)
                        prev = sl
                    self.movie.features[self.features[id]] = dyn
                    continue
                if id == 14:
#                    hist_val, bin_edges, patches = plt.hist(self.sls, 50, range=(0, 50), normed=True)
#                    ASL = np.mean(self.sls)
#                    MSL = np.median(self.sls)
#                    sigma = np.sqrt(2*np.log(ASL/MSL))
#                    x = np.linspace(min(bin_edges), max(bin_edges), 50)
#                    pdf = (np.exp(-(np.log(x) - MSL)**2 / (2 * sigma**2))/(x * sigma * np.sqrt(2 * np.pi)))
#                    test = pearsonr(pdf, hist_val)
#                    self.movie.features[self.features[id]] = test
                    continue
