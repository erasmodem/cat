from VideoAnalysis import *
from AudioAnalysis import *
import json

class CM():
    def __init__(self):
        self.movie = Movie()
        self.shots = []
        self.seqs = []
        self.current_shot = -1
        self.current_seq = -1
        self.workon = "full"
        self.va = VideoAnalysis()
        self.aa = AudioAnalysis()
        #self.gui = GUIwin()
        
    def shot_detect(self, thres, black_dur, pix_thres):
        self.update_analyzer()
        if self.movie.file == '':
            return False
        self.shots = self.va.extract_shots(thres, black_dur, pix_thres)
        if self.shots == []:
            return False
        else:
            self.movie.n_shots = len(self.shots)
            return True
        
    def shot_scale(self):
        self.update_analyzer()
        self.va.shot_scale(self.workon, self.current_shot, self.current_seq)

    def charachters_movement(self, caller):
        self.update_analyzer()
        self.va.movement_in_shot(self.workon, self.current_shot, self.current_seq)

    def camera_movement(self, caller):
        self.update_analyzer()
        self.va.camera_movement(self.workon, self.current_shot, self.current_seq)
    
    def shannon_entropy(self, caller):
        self.update_analyzer()
        self.va.shannon_entropy(self.workon, self.current_shot, self.current_seq)
    
    def get_contrast_brightness(self, caller):
        self.update_analyzer()
        self.va.contrast_brightness_saturation(self.workon, self.current_shot, self.current_seq)
        
    def get_color(self, caller):
        self.update_analyzer()
        self.va.color_table(self.workon, self.current_shot, self.current_seq)
        
    def video_analyze(self, caller):
        self.update_analyzer()
        self.va.feature_extraction()
        
    def segment_audio(self, caller):
        self.update_analyzer()
        self.aa.segment_track(self.workon, self.current_shot, self.current_seq)
    
    def classify_audio(self, caller):
        self.update_analyzer()
        self.aa.classify_track(self.workon, self.current_shot, self.current_seq)
    
    def estimate_split_edit(self, caller):
        self.update_analyzer()
        self.aa.estimate_split_edit(self.workon, self.current_shot, self.current_seq)
        
    def estimate_emotion(self, caller):
        self.update_analyzer()
        self.aa.speech_emotion(self.workon, self.current_shot, self.current_seq)
        
    def audio_analyze(self, caller):
        self.update_analyzer()
        self.aa.feature_extraction(self.workon, self.current_shot, self.current_seq)

    def update_analyzer(self):
        self.va.shots = self.shots
        self.va.seqs = self.seqs
        self.va.movie = self.movie
        self.aa.shots = self.shots
        self.aa.seqs = self.seqs
        self.aa.movie = self.movie
    
    def get_feature(self, name):
        dataFull, dataSeq, dataShot = [], [], []
        emptyValue = [False]*len(self.shots)
        for i, n in enumerate(self.aa.features+self.aa.nested_features):
            if n == name:
                type = self.aa.feat_type[1][self.aa.feat_type[0][i]]
                break
        for i, n in enumerate(self.va.features+self.va.nested_features):
            if n == name:
                type = self.va.feat_type[1][self.va.feat_type[0][i]]
                break
        for i, shot in enumerate(self.shots):
            if name in shot.aud_features:
                dataShot.append(shot.aud_features[name])
            elif name in shot.vid_features:
                dataShot.append(shot.vid_features[name])
            else:
                if name in ['Shot Scale', 'Pan Tilt', 'Lognormal Test', 
                            "Speech Music Silence", "Speaker Gender", 'Key&Scale']:
                    dataShot.append([0.0, 0.0])
                else:
                    dataShot.append(0.0)
                    emptyValue[i] = True
        if all(emptyValue):
            dataShot = []
        emptyValue = [False]*len(self.shots)
        for i, seq in enumerate(self.seqs):
            if name in seq.features:
                dataSeq.append(seq.features[name])
            else:
                dataSeq.append(0.0)
                emptyValue[i] = True
        if all(emptyValue):
            dataSeq = []
        if name in self.movie.features:
            dataFull = self.movie.features[name]
        return dataFull, dataSeq, dataShot, type
        
    def upload_data(self, caller, filename):
        pass
        
    def save_data(self, filename, data):
        author = data[0]
        company = data[1]
        comment = data[2]
        tags = data[3]
        self.movie.shots = self.shots
        self.movie.seqs = self.seqs
        with open(filename, 'w') as f:
            json.dump((author, company, comment, tags, self.movie), f)
            f.close()
    
    def load_data(self, caller):
        pass
    
    def search_data(self, caller, searchfor):
        pass
    
    def advanced_search(self):
        pass
        
