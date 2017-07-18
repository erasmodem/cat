import imdb
from pymediainfo import MediaInfo
from Util import get_fps, s_to_frames, hmsf_to_time

class Movie_info():
    
    def __init__(self):
        self.data = {}
        self.ia = imdb.IMDb('http')
        self.tv = False
        self.results = []
    
    def find_title(self, req):
        if self.tv == False:
            self.results = self.ia.search_movie(req)
        else:
            self.results = self.ia.search_episode(req)

    def assign_data(self,  id):
        self.ia.update(id)
        #va corretto il parse dei dati per i campi multipli
        self.data['Title'] = id.get('title').encode('utf-8')
        if id.get('year'):
            self.data['Year'] = id.get('year')
        else: self.data['Year'] = "-"
        if id.get('director'):
            self.data['Director'] = str(str(id.get('director')).split(">")[:]).split("_")[1].encode('utf-8')
            if len(str(id.get('director')).split(">")) > 2:
                self.data['Director'] += "  "+str(str(id.get('director')).split(">")[:]).split("_")[3].encode('utf-8')
        else: self.data['Director'] = "-"        
        if id.get('countries'):
            self.data['Country'] = str(str(id.get('countries')).split(">")[:]).split("'")[1].encode('utf-8')
            if len(str(id.get('countries')).split(">")) > 2:
                self.data['Country'] += "  "+str(str(id.get('countries')).split(">")[:]).split("_")[3].encode('utf-8')
        else: self.data['Country'] = "-"
        if id.get('runtimes'):
            self.data['Runtime'] = str(str(id.get('runtimes')).split(">")[:]).split("'")[1].encode('utf-8')
        else: self.data['Runtime'] = "-"
        if id.get('genres'):
            self.data['Genre'] = str(str(id.get('genres')).split(">")[:]).split("'")[1].encode('utf-8')
        else: self.data['Genre'] = "-"
        if id.get('writer'):
            self.data['Writer'] = str(str(id.get('writer')).split(">")[:]).split("_")[1].encode('utf-8')
        else: self.data['Writer'] = "-"
        if id.get('cast'):
            self.data['Cast'] = str(str(id.get('cast')).split(">")[:4]).split("_")[1].encode('utf-8')
#            if len(str(id.get('cast')).split(">")) > 2:
#                self.data['Cast'] += "  "+str(str(id.get('cast')).split(">")[:]).split("_")[3]
#            if len(str(id.get('cast')).split(">")) >= 3:
#                self.data['Cast'] += "\n\t\t  "+str(str(id.get('cast')).split(">")[:]).split("_")[5]
#            if len(str(id.get('cast')).split(">")) >= 4:
#                self.data['Cast'] += "  "+str(str(id.get('cast')).split(">")[:]).split("_")[7]
#            if len(str(id.get('cast')).split(">")) >= 5:
#                self.data['Cast'] += "\n\t\t  "+str(str(id.get('cast')).split(">")[:]).split("_")[9]
#            if len(str(id.get('cast')).split(">")) >= 6:
#                self.data['Cast'] += "  "+str(str(id.get('cast')).split(">")[:]).split("_")[11]
        else: self.data['Cast'] = "-"
        if id.get('cinematographer'):
            self.data['Cinematographer'] = str(str(id.get('cinematographer')).split(">")[:]).split("_")[1].encode('utf-8')
        else: self.data['Cinematographer'] = "-"
        if id.get('editor'):
            self.data['Editor'] = str(str(id.get('editor')).split(">")[:]).split("_")[1].encode('utf-8')
        else: self.data['Editor'] = "-"
        if id.get('composer'):
            self.data['Composer'] = str(str(id.get('composer')).split(">")[:]).split("_")[1].encode('utf-8')
        else: self.data['Composer'] = "-"
        if id.get('production manager'):
            self.data['Productor'] = str(str(id.get('production manager')).split(">")[:]).split("_")[1].encode('utf-8')
        else: self.data['Productor'] = " - "
        if id.get('production companies'):
            self.data['Production Company'] = str(str(id.get('production companies')).split(">")[:]).split("_")[1].encode('utf-8')
        else: self.data['Production Company'] = " - "
        if id.get('aspect ratio'):
            self.data['AspectRatio'] = str(id.get('aspect ratio')).encode('utf-8')
        else: self.data['AspectRatio'] = "-"
        if id.get('color info'):
            self.data['Color'] = str(id.get('color info')).split("'")[1].encode('utf-8')
        else: self.data['Color'] = "-"
        if id.get('languages'):
            self.data['Languages'] = str(str(id.get('languages')).split(">")[:]).split("'")[1].encode('utf-8')
            if len(str(id.get('languages')).split(">")) >= 2:
                self.data['Languages'] += "  "+str(str(id.get('languages')).split(">")[:]).split("_")[3].encode('utf-8')
        else: self.data['Languages'] = "-"
        if id.get('sound mix'):
            self.data['SoundMix'] = str(id.get('sound mix')).split("'")[1].encode('utf-8')
        else: self.data['SoundMix'] = "-"
        if id.get('cover url'):
            self.data['Poster'] = id.get('cover url')
        else: self.data['Poster'] = "-"
        if self.ia.get_imdbURL(id):
            self.data['Link'] = self.ia.get_imdbURL(id)
        else: self.data['Link'] = "-"
        
    def fill_label(self):
        return '''<u><b>MOVIE INFO</b></u>\n
                <b>Title:</b> {0}
                <b>Year:</b> {1}
                <b>Director:</b> {2}
                <b>Country:</b> {3}
                <b>Runtime:</b> {4} min
                <b>Genre:</b> {5}
                <b>Writer:</b> {6}
                <b>Cast:</b> {7}
                <b>Cinematographer:</b> {8}
                <b>Editor:</b> {9}
                <b>Composer:</b> {10}
                <b>Production:</b> {16} / {17}
                <b>Aspect Ratio:</b> {11}
                <b>Color:</b> {12}
                <b>Languages:</b> {13}
                <b>SoundMix:</b> {14}
                <b>IMDB url:</b> <a href="{15}">{15}</a>
                '''.format(self.data['Title'], self.data['Year'], self.data['Director'], 
                self.data['Country'], self.data['Runtime'], self.data['Genre'], self.data['Writer'], 
                self.data['Cast'], self.data['Cinematographer'], self.data['Editor'], 
                self.data['Composer'], self.data['AspectRatio'], self.data['Color'], 
                self.data['Languages'], self.data['SoundMix'], self.data['Link'], 
                self.data['Productor'], self.data['Production Company']).decode('utf-8')
        
    def get_data(self):
        if len(self.data) != 0:
            return self.data

class File_info():
    
    def __init__(self, file):
        self.data = {}
        self.file = file

    def assign_data(self):
        overall_bit="0"
        results = MediaInfo.parse(self.file)
        for track in results.tracks:
            if track.track_type=='General':
                self.data['Filepath'] = track.complete_name
                self.data['Language'] = track.audio_language_list
                if track.frame_rate is not None:
                    self.data['Framerate Num'] = float(track.frame_rate)
                else:
                    self.data['Framerate Num'] = get_fps(self.file)
                self.data['Codec'] = track.codec
                self.data['File Size'] = track.other_file_size[0]
                self.data['Duration'] = track.other_duration[0]
                duration_num = track.other_duration[3]
                self.data['Video Codec'] = track.codecs_video
                self.data['Audio Codec'] = track.audio_format_list
                self.data['Audio Tracks'] = track.count_of_audio_streams
                overall_bit = track.other_overall_bit_rate[0]
                if track.other_frame_rate is not None:
                    fr = track.other_frame_rate[0]
            if track.track_type=='Video':
                self.data['Color Space'] = track.color_space
                self.data['Bit Depth'] = track.other_resolution[0]
                if track.other_bit_rate is not None:
                    self.data['Video Bitrate'] = track.other_bit_rate[0]
                    overall_bit = "0"
                else:
                    self.data['Video Bitrate'] = overall_bit + " overall"
                self.data['Bits per Pixel'] = track.bits__pixel_frame
                self.data['Aspect Ratio'] = track.display_aspect_ratio
                self.data['Height'] = track.height
                self.data['Width'] = track.width
                if track.frame_rate_mode != 'VFR':
                    self.data['Frame Rate'] = fr
                else:
                    self.data['Frame Rate'] = "Variabile"
                if track.frame_count is not None:
                    self.data['Frame Count'] = int(track.frame_count)
                else:
                    timesec = hmsf_to_time(duration_num)
                    self.data['Frame Count'] = s_to_frames(timesec)
            if track.track_type=='Audio':
                self.data['Compression Mode'] = track.other_compression_mode[0]
                if overall_bit == "0":
                    self.data['Audio Bitrate'] = track.other_bit_rate[0]
                else:
                    self.data['Audio Bitrate'] = "Unavailable"
                self.data['Audio Format'] = track.format
                self.data['Channels'] = track.channel_s
                self.data['Sampling Rate'] = track.other_sampling_rate[0]
                
    def fill_label(self):
        return '''\n\t<u><b>FILE INFO</b></u>\n
                <b>Path:</b> {0}\t<b>Size:</b> {1}\t<b>Duration:</b> {2}\t<b>Framerate:</b> {3}\t<b>Codec:</b> {4}\n
                <b><u>Video</u></b>\t\t\t\t\t\t\t\t\t\t\t\t\t<b><u>Audio</u></b>\n
                <b><i>Video Codec</i></b>: {5}\t\t\t\t\t\t\t\t\t\t<b><i>Audio Codec</i></b>: {6}
                <b><i>Frame Size</i></b>: {7}x{8} <b><i>Aspect Ratio</i></b>: {11}\t\t\t\t\t<b><i>Bitrate</i></b>: {12} <b><i>Compression</i></b>: {10}
                <b><i>Bitrate</i></b>: {13} <b><i>Bits per Pixel</i></b>: {14}\t\t\t\t\t<b><i>Number of tracks</i></b>: {15} <b><i>Languages</i></b>: {16}
                <b><i>Color Space</i></b>: {17} <b><i>Depth</i></b>: {18}\t\t\t\t\t\t\t<b><i>Channels</i></b>: {19} <b><i>Sampling Rate</i></b>: {20}
        '''.format(self.data['Filepath'], self.data['File Size'], self.data['Duration'], 
                    self.data['Frame Rate'], self.data['Codec'], self.data['Video Codec'], 
                    self.data['Audio Codec'], self.data['Width'], self.data['Height'], 
                    self.data['Audio Format'], self.data['Compression Mode'], self.data['Aspect Ratio'], 
                    self.data['Audio Bitrate'], self.data['Video Bitrate'], self.data['Bits per Pixel'], 
                    self.data['Audio Tracks'], self.data['Language'], self.data['Color Space'], 
                    self.data['Bit Depth'], self.data['Channels'], self.data['Sampling Rate'])
