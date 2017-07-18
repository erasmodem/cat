from essentia.standard import *
import matplotlib.pyplot as plt
import numpy as np
from pyAudioAnalysis import audioSegmentation as aS
from pyAudioAnalysis import audioTrainTest as aT
import subprocess
from os import remove
from Util import audioFrames_to_s as af_to_s

class AudioAnalysis ():
    
    def __init__(self):
        self.audio_path = ''
        self.audio = None
        self.auMono = None
        self.auSegmented = None
        self.auClassified = None
        self.channels = 2
        self.sr = 48000.0
        self.duration = 0
        self.silence = []
        self.autocorr = None
        self.features = ['Enenrgy', 'Energy Entropy', 'Energy Flatness', 'RMS', 
                    'Zero Crossing Rate', 'Spectral Flatness', 'Spectral Flux',
                    'GFCC', 'Energy in ERB Bands', 'MFCC', 'Energy in Mel Bands', 'Energy in Bark Bands', 
                    'Energy in Frequency Bands', 'Spectral Centroid', 'Spectral Complexity', 
                    'Sound Wideness', 'Dynamic Complexity', 'Loudness', 'LARM Loudness', 
                    'Dissonance', 'Key&Scale', 'Onset Rate', 'BPM Estimation']
        self.nested_features = ["Split Edit", "Speech Music Silence", "Speaker Gender", 
                    'SpeechEmotion']
        self.feat_type = [[0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 
                        1, 1, 1, 0], 
                        ['line', 'multi', 'scalar', 'mat']]
        self.options = [False]*len(self.features)
        self.shots = []
        self.seqs = []
        self.movie = []
        self.configured = False
        
    def set_options(self, caller, id):
        self.options[id] = not self.options[id]
        
    def open_track(self):
        loader = AudioLoader(filename=self.audio_path)
        [self.audio, self.sr, self.channels, md5, bitrate, codec] = loader()
        monoLoader = MonoLoader(filename=self.audio_path, sampleRate=self.sr)
        self.auMono = monoLoader()
        fig, ax = plt.subplots(1, 1)
        dur = Duration(sampleRate=self.sr)
        self.duration = dur(self.auMono)
        #ax.plot(self.auMono)
        fig.subplots_adjust(left=0.03, bottom=0.06, right=1.0, top=1.0)
        self.configured = True
        return fig
    
    def segment_track(self):
        #Segment full track using the Bayesian Information Criterion
        #Build Feature Vector with frame size 1024
        
        audioM = self.auMono
        fc = FrameCutter(startFromZero=True,validFrameThresholdRatio=1)
        noframes = str(round(len(audioM)/1024.0))
        af = fc(audioM)
        mfcc1, mfcc2, mfcc3, mfcc4, mfcc5, mfcc6 = [], [], [], [], [], []
        mfcc7, mfcc8, mfcc9, mfcc10, mfcc11, mfcc12, mfcc13 = [], [], [], [], [], [], []
        flux, zcr, energy= [], [], []
        i=1
        while len(af) != 0:
            sp = Spectrum(size=len(af))
            spectrum = sp(af)
            mc = MFCC(inputSize=len(spectrum), sampleRate=self.sr)
            mcs = mc(spectrum)
            mfcc1.append(mcs[1][0])
            mfcc2.append(mcs[1][1])
            mfcc3.append(mcs[1][2])
            mfcc4.append(mcs[1][3])
            mfcc5.append(mcs[1][4])
            mfcc6.append(mcs[1][5])
            mfcc7.append(mcs[1][6])
            mfcc8.append(mcs[1][7])
            mfcc9.append(mcs[1][8])
            mfcc10.append(mcs[1][9])
            mfcc11.append(mcs[1][10])
            mfcc12.append(mcs[1][11])
            mfcc13.append(mcs[1][12])
            sfl = Flux()
            flux.append(sfl(spectrum))
            zc = ZeroCrossingRate()
            zcr.append(zc(af))
            en = Energy()
            energy.append(en(af))
            af = fc(audioM)
            print(str(i)+"/"+noframes)
            i+=1
        mfcc1 = np.array(mfcc1, dtype='single')
        mfcc2 = np.array(mfcc2, dtype='single')
        mfcc3 = np.array(mfcc3, dtype='single')
        mfcc4 = np.array(mfcc4, dtype='single')
        mfcc5 = np.array(mfcc5, dtype='single')
        mfcc6 = np.array(mfcc6, dtype='single')
        mfcc7 = np.array(mfcc7, dtype='single')
        mfcc8 = np.array(mfcc8, dtype='single')
        mfcc9 = np.array(mfcc9, dtype='single')
        mfcc10 = np.array(mfcc10, dtype='single')
        mfcc11 = np.array(mfcc11, dtype='single')
        mfcc12 = np.array(mfcc12, dtype='single')
        mfcc13 = np.array(mfcc13, dtype='single')
        flux = np.array(flux, dtype='single')
        zcr = np.array(zcr, dtype='single')
        energy = np.array(energy, dtype='single')
        feature_vector = np.matrix((mfcc1,mfcc2,mfcc3,mfcc4,mfcc5,mfcc6,mfcc7,
                    mfcc8,mfcc9,mfcc10,mfcc11,mfcc12,mfcc13, flux, zcr, energy))

        segBic = SBic(minLength=int(self.sr/512))
        seg_frames = segBic(feature_vector)
        self.auSegmented = af_to_s(seg_frames, self.sr, vector=True)
        
    def estimate_split_edit(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False or len(self.shots)==0:
            return
        self.movie.features['Split Edit Timings'] = []
        if self.auSegmented == None:
            self.segment_track()
        
        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]
        idx = 0
        for shot in area:
            exact, cont = [], []
            Jcut = []
            Lcut = []
            video_cut = shot.endns/1000000000
            audio_cut = self.auSegmented[idx]
            #modificare, cosi niente Jcut
            while audio_cut < video_cut:
                idx +=1
                audio_cut = self.auSegmented[idx]
            if audio_cut <= video_cut+0.2 and audio_cut >= video_cut-0.2:
                exact.append([audio_cut, video_cut])
            elif audio_cut <= video_cut+3:
                Lcut.append([audio_cut, video_cut])
            else:
                audio_cut = self.auSegmented[idx-1]
                if audio_cut >= video_cut-3:
                    Jcut.append([audio_cut, video_cut])
            shot.aud_features['Split Edit'] = [len(Jcut), len(exact), len(Lcut),  len(cont)]
            self.movie.features['Split Edit Timings'].append([Jcut, exact, Lcut])
            print(str(shot.index)+"/"+str(len(area))+" Shots")
                
    def classify_track(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False or len(self.shots)==0:
            return
        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]
            
        self.get_silence()
        silSlice = np.delete(self.silence, np.s_[2], axis=1)
        spec = ['silence']*len(silSlice)
        silSlice = zip(silSlice, spec)
        resSM = aS.mtFileClassification(self.audio_path, "Classifier/svmSM", "svm", False)
        #resFM = aS.mtFileClassification(self.audio_path, "Classifier/knnSpeakerFemaleMale", "knn", False)
        #insert silence slices replacing previous classification
        sm = zip(resSM[4],resSM[5])
        i=0
        for sil in silSlice:
            j = 1
            while sm[i][0][1] < sil[0][0]:
                i +=1
            sm[i][0][1] = sil[0][0]
            if i == len(sm)-1:
                i -=1
            while sm[i+j][0][0] < sil[0][1]:
                j += 1
                if i+j ==len(sm):
                    break
            if j == 1:
                j +=1
            sm[i+j-1][0][0] = sil[0][1]
            del sm[i+1:i+j-1]
            sm.insert(i+1, ([sm[i][0][1],sm[i+2][0][0]],'silence'))
            
        self.assign_data(area, sm, "Speech Music Silence", False)
        #sg = zip(resFM[4], resFM[5])
        #self.assign_data(area, sg, "Speaker Gender", False)
    
    def get_silence(self, threshold=24, duration=2):
        self.silence = []
        proc = subprocess.Popen(("ffmpeg", 
                                    "-i",
                                    self.audio_path,
                                    "-af",
                                    "silencedetect=n=-"
                                    + str(threshold) +
                                    "dB:d=" + str(duration), 
                                    "-f", "null", "-"),
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)
        output = proc.stdout.read()
        for i, line in enumerate(output.split('\n')[31:-3]):
            el = line.split('_')
            if len(el) == 2:
                silstart = float(el[1].split(': ')[1])
            elif len(el) == 3:
                silend = float(el[1].split(': ')[1].split(' |')[0])
                sildur = float(el[2].split(': ')[1])
                self.silence.append((silstart, silend, sildur))
            else:
                continue
        
    def speech_emotion(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False or len(self.shots)==0:
            return
        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]
        
        for shot in area:
            tr = Trimmer(sampleRate=self.sr, startTime=shot.startns/1000000000.0, endTime=shot.endns/1000000000.0)
            audioM = tr(self.auMono)
            path = "au_"+str(shot.index)+".wav"
            mw = MonoWriter(filename=path, sampleRate=self.sr)
            mw(audioM)
            val_aro = aT.fileRegression(path, "Classifier/svmSpeechEmotion", "svm")
            shot.aud_features["SpeechEmotion"] = val_aro[0]
            remove(path)
            print(str(shot.index)+"/"+str(len(area))+" Shots")
    
    def feature_extraction(self, workarea="full", current_shot=0, current_seq=0):
        if self.configured == False or len(self.shots)==0:
            return
        if workarea == 'full':
            area = self.shots
        elif workarea == 'seq':
            area = self.seqs[current_seq].shots[0]
        elif workarea == 'shot':
            area = [self.shots[current_shot]]
        
        for shot in area:
            tr = Trimmer(sampleRate=self.sr, startTime=shot.startns/1000000000.0, endTime=shot.endns/1000000000.0)
            audioM = tr(self.auMono)
            audioM[audioM==0]=0.000001
            if self.channels >= 2:
                strim = StereoTrimmer(sampleRate=self.sr, startTime=shot.startns/1000000000.0, endTime=shot.endns/1000000000.0)
                audioS = strim(self.audio)
            if len(audioM)%2 != 0:
                audioM = audioM[:-1]
                #audioM = np.array(np.append(audioM, 0.0), dtype="single")
            sp = Spectrum(size=len(audioM))
            spectrum = sp(audioM)
            for id, todo in enumerate(self.options):
                if todo:
                    if id == 0:
                        en = Energy()
                        shot.aud_features[self.features[id]] = en(audioM)
                        continue
                    if id == 1:
                        ee = Entropy()
                        shot.aud_features[self.features[id]] = ee(abs(audioM))
                        continue
                    if id == 2:
                        fl = Flatness()
                        shot.aud_features[self.features[id]] = fl(abs(audioM))
                        continue
                    if id == 3:
                        rms = RMS()
                        shot.aud_features[self.features[id]] = rms(audioM)
                        continue
                    if id == 4:
                        zc = ZeroCrossingRate()
                        shot.aud_features[self.features[id]] =  zc(audioM)
                        continue
                    if id == 5:
                        sf = FlatnessDB()
                        shot.aud_features[self.features[id]] = sf(abs(audioM))
                        continue
                    if id == 6:
                        sfl = Flux()
                        spf = Spectrum()
                        fc = FrameCutter(frameSize=int(self.sr/2),hopSize=int(self.sr/4))
                        nof = (shot.lengthns/1000000000)*4
                        frameNum = 1
                        flux = []
                        while frameNum < nof:
                            frame = fc(audioM)
                            spectF = spf(frame)
                            flux.append(sfl(spectF))
                            frameNum += 1
                        shot.aud_features[self.features[id]] = np.median(flux)
                        #dati a salti di samplerate/4 frame
                        continue
                    if id == 7:
                        gc = GFCC(inputSize=len(spectrum), sampleRate=self.sr, lowFrequencyBound=20, logType='dbpow')
                        res = gc(spectrum)
                        shot.aud_features[self.features[id]] = res[1]
                        continue
                    if id == 8:
                        gc = GFCC(inputSize=len(spectrum), sampleRate=self.sr, lowFrequencyBound=20, logType='dbpow')
                        res = gc(spectrum)
                        shot.aud_features[self.features[id]] = res[0]
                        continue
                    if id == 9:    
                        mc = MFCC(inputSize=len(spectrum), sampleRate=self.sr, lowFrequencyBound=20, highFrequencyBound = 12000, 
                                type='magnitude', weighting='linear', warpingFormula='htkMel', logType='log', numberBands=24, 
                                numberCoefficients=6, normalize = 'unit_max', dctType=3, liftering=22)
                        shot.aud_features[self.features[id]] = mc(spectrum)[1]
                        continue
                    if id == 10:
                        mc = MFCC(inputSize=len(spectrum), sampleRate=self.sr, lowFrequencyBound=20, highFrequencyBound = 12000, 
                                type='magnitude', weighting='linear', warpingFormula='htkMel', logType='log', numberBands=24, 
                                numberCoefficients=6, normalize = 'unit_max', dctType=3, liftering=22)
                        shot.aud_features[self.features[id]] = mc(spectrum)[0]
                        continue
                    if id == 11:
                        bb = BarkBands(sampleRate=self.sr, numberBands=24)
                        shot.aud_features[self.features[id]] = bb(spectrum)
                        continue
                    if id == 12:
                        fb = FrequencyBands(sampleRate=self.sr, frequencyBands=[20, 60, 250, 500, 2000, 6000, 12000, 20000])
                        shot.aud_features[self.features[id]] = fb(spectrum)
                        continue
                    if id == 13:
                        sct = SpectralCentroidTime(sampleRate=self.sr)
                        shot.aud_features[self.features[id]] = sct(audioM)
                        continue
                    if id == 14:
                        sc = SpectralComplexity(sampleRate=self.sr, magnitudeThreshold=500)
                        shot.aud_features[self.features[id]] = sc(spectrum)
                        continue
                    if id == 15:
                        #Negative if center prevails, positive if sides prevail
                        if self.channels<2:
                            continue
                        sd = StereoDemuxer()
                        [Left, Right] = sd(audioS)
                        if len(Left)%2 != 0:
                            Left = np.array(np.append(Left, 0.0), dtype="single")
                            Right = np.array(np.append(Right, 0.0), dtype="single")
                        sps = Spectrum()
                        sL = sps(Left)
                        sR = sps(Right)
                        pan = Panning(sampleRate=self.sr, averageFrames=len(Left), panningBins=3,numCoeffs=3)
                        arr = pan(sL, sR)
                        arr += max(np.absolute(arr))
                        l, c, r = arr[0]
                        shot.aud_features[self.features[id]] = 1-(c-l-r)
                        continue
                    if id == 16:
                        dc = DynamicComplexity()
                        shot.aud_features[self.features[id]] = dc(audioM)[0]
                        continue
                    if id == 17:
                        lo = Loudness()
                        shot.aud_features[self.features[id]] = lo(audioM)
                        continue
                    if id == 18:
                        lr = Larm(sampleRate=self.sr)
                        shot.aud_features[self.features[id]] = lr(audioM)
                        continue
                    if id == 19:
                        spk = SpectralPeaks(maxFrequency=10000, sampleRate=self.sr)
                        [freqs, mags] = spk(audioM)
                        di = Dissonance()
                        shot.aud_features[self.features[id]] = di(freqs, mags)
                        continue
                    if id == 20:
                        k = KeyExtractor()
                        ks = k(audioM)
                        if ks[1] == 'major':
                            mode = 2
                        elif ks[1] == 'minor':
                            mode = 1
                        shot.aud_features[self.features[id]] = [mode, ks[0]+' '+ks[1]]
                        continue
                    if id == 21:
                        res = Resample(inputSampleRate=self.sr, quality=0)
                        audio44 = res(audioM)
                        osr = OnsetRate()
                        shot.aud_features[self.features[id]] = osr(audio44)[1]
                        continue
                    if id == 22:
                        bpm = PercivalBpmEstimator(sampleRate=int(self.sr))
                        shot.aud_features[self.features[id]] = bpm(audioM)
                        continue
            print(str(shot.index)+"/"+str(len(area))+" Shots")
            
    def assign_data(self, area, feature, name, mean):
        lim = len(feature)
        for shot in area:
            i=0
            while i<lim and feature[i][0][1]<=shot.startns/1000000000.0:
                i+=1
            start = i
            while i<lim and feature[i][0][0]<shot.endns/1000000000.0:
                i+=1
            data = feature[start:i]
            sil, mus, sp, male, female = 0, 0, 0, 0, 0
            for seg in data:
                if seg[1] == 'silence':
                    sil +=(seg[0][1]-seg[0][0])
                elif seg[1] == 'music':
                    mus +=(seg[0][1]-seg[0][0])
                elif seg[1] == 'speech':
                    sp +=(seg[0][1]-seg[0][0])
                elif seg[1] == 'male':
                    male +=(seg[0][1]-seg[0][0])
                elif seg[1] == 'female':
                    female +=(seg[0][1]-seg[0][0])
            if name == "Speech Music Silence":
                shot.aud_features[name] = [sp, mus, sil]
            elif name == "Speaker Gender":
                shot.aud_features[name] = [male, female]

if __name__ == '__main__':
    aa = AudioAnalysis()
    aa.audio_path= "/home/erasmo/Scrivania/CM+/RDM_audio.wav"
    aa.channels=2
