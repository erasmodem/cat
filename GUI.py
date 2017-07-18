from __future__ import division, print_function, unicode_literals
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FC
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NT
import matplotlib.pyplot as plt
from numpy import arange, polyfit, poly1d
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstPlayer', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gtk, Gst, Gdk, GdkX11, GstPlayer, GstVideo, GdkPixbuf
#from ctypes import CDLL
import magic, re, urllib2, thread, time, os
#import sys
#sys.setdefaultencoding('utf8')
from Util import *
from CM import *

class VideoBox(Gtk.VBox):
    
    def __init__(self, p):
        Gtk.VBox.__init__(self)
        self.parent = p
        self.fname = ""
        self.out = 100
        self.manual_seek = True
        self.frame = Gtk.DrawingArea()
        self.frame.override_background_color(0, Gdk.RGBA(0,0,0,1))
        self.toolbar = self.get_toolbar()
        self.pack_start(self.frame, expand=True, fill=True, padding=0)
        self.pack_start(self.toolbar, expand=False, fill=True, padding=0)
        self.show_all()

        self.player = GstPlayer.Player.new()
        bus = self.player.get_pipeline().get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)

    def get_toolbar(self):
        rect = Gtk.HBox(False, 2)
        tb = Gtk.Toolbar()
        tb.set_style(Gtk.ToolbarStyle.ICONS)
        for text, tooltip, stock, callback in (
            (("Play"), ("Play"), Gtk.STOCK_MEDIA_PLAY, lambda b: self.play()),
            (("Pause"), ("Pause"), Gtk.STOCK_MEDIA_PAUSE, lambda b: self.pause()),
            (("Previous Frame"), ("Previous Frame"), Gtk.STOCK_MEDIA_PREVIOUS, lambda b: self.prevframe()), 
            (("Next Frame"), ("Next Frame"), Gtk.STOCK_MEDIA_NEXT, lambda b: self.nextframe()),
            (("Stop"), ("Stop"), Gtk.STOCK_MEDIA_STOP, lambda b: self.stop())
            ):
            b=Gtk.ToolButton(stock)
            b.set_tooltip_text(tooltip)
            b.connect("clicked", callback)
            tb.insert(b, -1)
        self.seekbar = Gtk.HScale()
        self.seekbar.set_range(0, 0)
        self.seekbar.set_digits(2)
        self.seekbar.set_draw_value(False)
        self.seekbar.connect('value-changed', self.seekpos)
        self.time_label = Gtk.Entry()
        self.time_label.set_input_purpose(Gtk.InputPurpose.NUMBER)
        self.time_label.set_width_chars(11)
        self.time_label.set_text("00:00:00.00")
        self.time_label.connect("activate", self.seekpos, "entry")
        rect.pack_start(tb, False, False, 0)
        rect.pack_start(self.seekbar, True, True, 0)
        rect.pack_start(self.time_label, False, False, 0)
        return rect
    
    def play_thread(self):
        play_thread_id = self.play_thread_id
        while play_thread_id == self.play_thread_id:
            pos_int = self.player.get_pipeline().query_position(Gst.Format.TIME)[1]
            pos_str = time_to_hmsf(pos_int, nanos=True, string=True)
            pos_frm = s_to_frames(pos_int, nanos=True)
            if play_thread_id == self.play_thread_id:
                Gdk.threads_enter()
                self.time_label.set_text(pos_str)
                self.seekbar.set_value(pos_frm)
                self.parent.update_position()
                Gdk.threads_leave()
            time.sleep(0.03)
            
    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.player.stop()
        elif t == Gst.MessageType.ERROR:
            self.player.stop()
            err, debug = message.parse_error()
            print ("Error: %s" % err, debug)
            
    def on_sync_message(self, bus, message):
        if message.get_structure() is None:
            return
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(self.frame.get_window().get_xid())
        if message.get_structure.get_name() == 'prepare-xwindow-id':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_xwindow_id(self.frame.get_window().xid)
            
    def seekpos(self, caller, *arg):
        if (self.player.props.uri != None) and (self.manual_seek == True):
            #click on the seekbar
            if len(arg) == 0:
                pos = self.seekbar.get_value()
                self.player.seek(framestep*pos)
                self.time_label.set_text(time_to_hmsf(frames_to_s(pos, nanos=True), True, True))
            #new position in the entry tab
            elif arg[0] == 'entry':
                pos = self.time_label.get_text()
                npos = hmsf_to_time(pos, nanos=True)
                self.player.seek(npos)
                self.seekbar.set_value(s_to_frames(npos, nanos=True))
            #seek to shot change
            else:
                pos = arg[0]
                posns = hmsf_to_time(pos, nanos=True)
                self.player.seek(posns)
                self.time_label.set_text(pos)
                self.manual_seek = False
                self.seekbar.set_value(s_to_frames(posns, nanos=True))
                self.manual_seek = True
            self.parent.update_position()
            #update frame
            #self.player.pause()
                
    def nextframe(self):
        self.manual_seek = False
        self.player.pause()
        pos = self.seekbar.get_value()
        if pos < self.out:
            self.seekbar.set_value(pos+1)
            newpos = self.player.get_position() + framestep
            self.player.seek(newpos)
            self.time_label.set_text(time_to_hmsf(newpos, True, True))
        self.parent.update_position()
        self.manual_seek = True

    def prevframe(self):
        self.manual_seek = False
        self.player.pause()
        pos = self.seekbar.get_value()
        if pos > 0:
            self.seekbar.set_value(pos-1)
            newpos = self.player.get_position() - framestep
            self.player.seek(newpos)
            self.time_label.set_text(time_to_hmsf(newpos, True, True))
        self.parent.update_position()
        self.manual_seek = True
        
    def play(self):
        self.manual_seek = False
        self.player.play()
        self.play_thread_id = thread.start_new_thread(self.play_thread, ())
    
    def pause(self):
        self.player.pause()
        self.play_thread_id = None
        self.manual_seek = True
        
    def stop(self):
        self.time_label.set_text("00:00:00.00")
        self.player.stop()
        self.manual_seek = True
        self.seekbar.set_value(0)
        self.player.seek(0)
        #To render the first frame
        self.player.pause()
        self.play_thread_id = None
    
    def mute(self, handler):
        if self.player.get_mute():
            self.player.set_mute(False)
        else:
            self.player.set_mute(True)
        
class CmGUI(Gtk.Window):

    def __init__(self):
        #Main window
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        self.set_title("CAT")
        self.set_border_width(3)
        self.set_default_size(1600, 900)
        self.connect("delete-event", Gtk.main_quit)
        self.set_position(Gtk.WindowPosition.CENTER)
        mainbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 2)
        self.videoplayer = VideoBox(self)
        self.videoplayer.set_size_request(640, 480)
        self.videoplayer2 = VideoBox(self)
        self.videoplayer2.set_size_request(640, 480)
        self.fig, self.fc = None, None
        self.view = 'raw'
        self.draw_trendline = False
        self.degree = 1
        self.cm = CM()
        
        #Menu 
        mb = self.BuildMenu()

        #Notebook design
        notebook = Gtk.Notebook()
        
        #MAIN PAGE
        page1 = Gtk.HBox()
        page1.set_border_width(2)
        page1.set_spacing(1)
        notebook.append_page(page1, Gtk.Label('Main'))

        b11 = Gtk.Button(label="Open Video")
        b11.connect("clicked", self.OpenFile)
        b12 = Gtk.Button(label="Rip Dvd")
        b12.connect("clicked", self.rip_source)
        b13 = Gtk.Button(label="Rip BluRay")
        b13.connect("clicked", self.rip_source)
        self.progbar = Gtk.ProgressBar()
        self.progbar.set_pulse_step(0.01)
        self.progbar.set_show_text(True)
        c_but = Gtk.Button(label="Cancel")
        c_but.connect("clicked", lambda exe: self.terminate_proc())
        b14 = Gtk.Button(label="Cut Title and Extract Audio Track")
        b14.connect("clicked", self.cut_extract)
        
        self.start_time_entry = Gtk.Entry()
        start_time_set = Gtk.Button(label="Set Start Time")
        start_time_set.connect("clicked", lambda t: self.start_time_entry.set_text(self.videoplayer.time_label.get_text()))
        self.end_time_entry = Gtk.Entry()
        end_time_set = Gtk.Button(label="Set End Time")
        end_time_set.connect("clicked", lambda t: self.end_time_entry.set_text(self.videoplayer.time_label.get_text()))

        self.fileinfo = Gtk.Label()
        self.fileinfo.set_size_request(-1, 350)
        
        self.movieinfo = Gtk.Label()
        self.movieinfo.set_size_request(300, -1)
        
        self.searchentry = Gtk.SearchEntry()
        self.searchentry.set_placeholder_text("Search for a movie to analyze")
        
        searchtype = Gtk.HBox()
        movie_radio = Gtk.RadioButton.new_with_label(None, "Movie")
        movie_radio.connect("toggled", self.movsearch)
        searchtype.pack_start(movie_radio, False,  False, 0)
        tv_radio = Gtk.RadioButton.new_with_label_from_widget(movie_radio,"Tv")
        tv_radio.connect("toggled", self.tvsearch)
        searchtype.pack_start(tv_radio, False,  False, 0)
        
        searchbutton = Gtk.Button(label="Search Movie")
        searchbutton.connect("clicked", self.SearchMovieInfo)
        self.searchcombo = Gtk.ComboBoxText()
        self.searchcombo.connect("changed", self.GetMovieInfo)
        
        self.poster = Gtk.Image()
        self.poster.set_size_request(200, -1)
        
        box11 = Gtk.VBox()
        self.box12 = Gtk.HBox()
        box13 = Gtk.VButtonBox()
        box13.set_size_request(50, -1)
        box13.set_spacing(6)
        box13.set_layout(3)
        box13.set_border_width(3)
        box14 = Gtk.VBox()
        box14.set_size_request(50, -1)
        box14.set_spacing(3)
        box14.set_homogeneous(False)
        box14.set_border_width(3)
        
        for b in [b11, b12, b13, self.progbar, c_but, Gtk.HSeparator(), start_time_set, 
                    self.start_time_entry, end_time_set, self.end_time_entry, b14]:
            box13.pack_start(b, True, False, 1)
        self.box12.pack_start(box13,False, False, 0 )
        self.box12.pack_start(self.videoplayer, True, True, 0)
        box11.pack_start(self.box12, True, True, 0)
        box11.pack_start(self.fileinfo, False, False, 0)
        box14.pack_start(self.searchentry, False, False, 0)
        box14.pack_start(searchtype, False, False, 0)
        box14.pack_start(searchbutton, False, False, 0)
        box14.pack_start(self.searchcombo, False, False, 0)
        box14.pack_start(self.movieinfo, False, False, 0)
        box14.pack_start(self.poster, False, False, 0)
        page1.pack_start(box11, True, True, 0)
        page1.pack_start(box14, False, False, 0)
        
        #VIDEO ANALYSIS PAGE
        page2 = Gtk.HBox()
        page2.set_border_width(3)
        notebook.append_page(page2, Gtk.Label('Video Analysis'))
        
        b21 = Gtk.Button(label="Shot Detect")
        b21.connect("clicked", self.shot_detect)
        b21b = Gtk.CheckButton(label="Edit Shots")
        b21b.connect("toggled", self.edit_shots)
        b22 = Gtk.CheckButton(label="Edit Sequences")
        b22.connect("toggled", self.edit_sequences)
        b23 = Gtk.Button(label="Shot Scale")
        b23.connect("clicked", self.shot_scale)
        b25 = Gtk.Button(label="Charachters Movement")
        b25.connect("clicked", self.cm.charachters_movement)
        b25b = Gtk.Button(label="Camera Movement")
        b25b.connect("clicked", self.cm.camera_movement)
        b25c = Gtk.Button(label="Shannon Entropy")
        b25c.connect("clicked", self.cm.shannon_entropy)
        b26 = Gtk.Button(label="Get Contrast/Brightness/Saturation")
        b26.connect("clicked", self.cm.get_contrast_brightness)
        b27 = Gtk.Button(label="Get Color table")
        b27.connect("clicked", self.cm.get_color)
        b28 = Gtk.Button(label="Acquire frame")
        b28.connect("clicked", self.acquire_frame)
        b29 = Gtk.Button(label="Extract Features")
        b29.connect("clicked", self.cm.video_analyze)
        
        mute = Gtk.CheckButton.new_with_label("Play mute")
        mute.set_active(True)
        mute.connect('toggled', self.videoplayer2.mute)
        
        th_label = Gtk.Label("New Scene Threshold")
        self.thres_scale = Gtk.HScale()
        self.thres_scale.set_range(0, 1)
        self.thres_scale.set_digits(2)
        self.thres_scale.set_value(0.2)
        bl_label = Gtk.Label("Black Duration")
        self.blackdur_scale = Gtk.HScale()
        self.blackdur_scale.set_range(0, 3)
        self.blackdur_scale.set_digits(1)
        self.blackdur_scale.set_value(0.1)
        px_label = Gtk.Label("Black Pixel Threshold")
        self.pix_thres = Gtk.HScale()
        self.pix_thres.set_range(0, 1)
        self.pix_thres.set_digits(2)
        self.pix_thres.set_value(0.05)
        
        self.listore = Gtk.ListStore(int, str, str, str, str, str, str)
        self.current_view = "Shots"
        self.view_filter = self.listore.filter_new()
        self.view_filter.set_visible_func(self.filter_func)
        self.treeview = Gtk.TreeView.new_with_model(self.view_filter)
        select = self.treeview.get_selection()
        select.set_mode(Gtk.SelectionMode.SINGLE)
        select.connect("changed", self.row_selected)
        
        for i, column_title in enumerate(["Index", "Start Time", "End Time", 
                                        "Duration", "Title", "Notes", "Type", "Shot", "Char Num"]):
            renderer = Gtk.CellRendererText()
            renderer.set_alignment(0.5, 0.5)
            if column_title == "Notes":
                renderer.set_property("editable", True)
                renderer.connect("edited", self.add_notes)
            if column_title == "Title":
                renderer.set_property("editable", True)
                renderer.connect("edited", self.add_title)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            if column_title != "Index":
                column.set_expand(True)
            column.set_alignment(0.5)
            if column_title in ("Type", "Title", "Shot", "Char Num"):
                column.set_visible(False)
            self.treeview.append_column(column)

        #put the treeview in a scrollwindow
        scrollbox = Gtk.ScrolledWindow()
        scrollbox.set_hexpand(False)
        scrollbox.set_vexpand(True)
        scrollbox.set_size_request(-1, 200)
        scrollbox.add(self.treeview)
        
        #creating buttons to filter by shot or sequence view
        filter_buttons = Gtk.HBox()
        for name in ["Shots", "Sequences"]:
            button = Gtk.Button(name)
            filter_buttons.add(button)
            button.connect("clicked", self.on_selection_button_clicked)

        shottb = Gtk.Toolbar()
        shottb.set_style(Gtk.ToolbarStyle.BOTH)
        for label, tooltip, stock, callback in (
            (("Previous Shot"), ("Previous Shot"), Gtk.STOCK_GO_BACK, lambda b:self.shot_prev()),
            (("Next Shot"), ("Next Shot"), Gtk.STOCK_GO_FORWARD, lambda b:self.shot_next()), 
            (("Add Cut"), ("Add Cut"), Gtk.STOCK_ADD, lambda b:self.shot_add()), 
            (("Fix Cut"), ("Fix Cut"), Gtk.STOCK_APPLY, lambda b:self.shot_fix()),
            (("Delete Shot"), ("Delete Shot"), Gtk.STOCK_REMOVE, lambda b:self.shot_del())
            ):
            b=Gtk.ToolButton(stock)
            b.set_label(label)
            b.set_tooltip_text(tooltip)
            b.connect("clicked", callback)
            shottb.insert(b, -1)
        self.shotbox = Gtk.VBox()
        self.shotbox.add(shottb)
        
        seqtb = Gtk.Toolbar()
        seqtb.set_style(Gtk.ToolbarStyle.BOTH)
        for label, tooltip, stock, callback in (
            (("Previous Shot"), ("Previous Shot"), Gtk.STOCK_GO_BACK, lambda b:self.shot_prev()),
            (("Next Shot"), ("Next Shot"), Gtk.STOCK_GO_FORWARD, lambda b:self.shot_next()), 
            (("Add Blank Row"), ("Add Blank Row"), Gtk.STOCK_ADD, lambda b:self.add_blank_seq_row()),
            (("Set Start Time"), ("Set Start Time"), Gtk.STOCK_GOTO_FIRST, lambda b: self.set_time("start")),
            (("Set End Time"), ("Set End Time"), Gtk.STOCK_GOTO_LAST, lambda b: self.set_time("end")),
            (("Add Sequence"), ("Add Sequence"), Gtk.STOCK_OK, lambda b:self.seq_add()),
            (("Previous Sequence"), ("Previous Sequence"), Gtk.STOCK_MEDIA_PREVIOUS, lambda b:self.seq_prev()), 
            (("Next Sequence"), ("Next Sequence"), Gtk.STOCK_MEDIA_NEXT, lambda b:self.seq_next()), 
            (("Fix Sequence"), ("Fix Sequence"), Gtk.STOCK_APPLY, lambda b:self.seq_fix()), 
            (("Delete Sequence"), ("Delete Sequence"), Gtk.STOCK_REMOVE, lambda b:self.seq_del())
            ):
            b=Gtk.ToolButton(stock)
            b.set_label(label)
            b.set_tooltip_text(tooltip)
            b.connect("clicked", callback)
            seqtb.insert(b, -1)
        self.seqbox = Gtk.VBox()
        self.seqbox.add(seqtb)
        
        self.current_label = Gtk.Label()
        self.current_label.set_markup("Edit Shot: "+"in Sequence: ")
        
        options_box2= Gtk.Grid()
        y = -1
        for x, label in enumerate(self.cm.va.features):
            b = Gtk.CheckButton.new_with_label(label)
            b.connect("toggled", self.cm.va.set_options, x)
            y +=1
            options_box2.attach(b, 0, y, 1, 1)
        
        box21 = Gtk.VBox()
        box21.set_size_request(170, -1)
        box21.set_spacing(3)
        box21.pack_start(b21, expand=False, fill=True, padding=0)
        box21.pack_start(th_label, expand=False, fill=True, padding=0)
        box21.pack_start(self.thres_scale, expand=False, fill=True, padding=0)
        box21.pack_start(bl_label, expand=False, fill=True, padding=0)
        box21.pack_start(self.blackdur_scale, expand=False, fill=True, padding=0)
        box21.pack_start(px_label, expand=False, fill=True, padding=0)
        box21.pack_start(self.pix_thres, expand=False, fill=True, padding=0)
        box21.pack_start(b21b, expand=False, fill=True, padding=0)
        box21.pack_start(b22, expand=False, fill=True, padding=0)
        box21.pack_start(self.current_label, expand=False, fill=True, padding=0)
        box21.pack_start(self.buildSelector(), False, True, 0)
        self.box22 = Gtk.VBox()
        self.box22.set_border_width(6)
        self.box22.pack_start(self.videoplayer2, expand=True, fill=True, padding=0)
        self.box22.pack_start(self.shotbox, expand=False, fill=True, padding=0)
        self.box22.pack_start(self.seqbox, expand=False, fill=True, padding=0)
        box23 = Gtk.VBox()
        box23.set_size_request(200, -1)
        box23.set_border_width(6)
        box23.pack_start(scrollbox, expand=False, fill=True, padding=0)
        box23.pack_start(filter_buttons, expand=False, fill=True, padding=0)
        box25 = Gtk.VBox()
        box25.pack_start(self.box22, expand=True, fill=True, padding=0)
        box25.pack_start(box23, expand=False, fill=True, padding=0)
        box24 = Gtk.VBox()
        box24.set_spacing(3)
        box24.pack_start(mute, expand=False, fill=True, padding=0)
        box24.pack_start(b23, expand=False, fill=True, padding=0)
        box24.pack_start(b25, expand=False, fill=True, padding=0)
        box24.pack_start(b25b, expand=False, fill=True, padding=0)
        box24.pack_start(b25c, expand=False, fill=True, padding=0)
        box24.pack_start(b26, expand=False, fill=True, padding=0)
        box24.pack_start(b27, expand=False, fill=True, padding=0)
        box24.pack_start(b29, expand=False, fill=True, padding=0)
        box24.pack_start(options_box2, expand=False, fill=True, padding=0)
        box24.pack_start(b28, expand=False, fill=True, padding=0)
        
        page2.pack_start(box21, expand=False, fill=True, padding=0)
        page2.pack_start(box25, expand=True, fill=True, padding=0)
        page2.pack_start(box24, expand=False, fill=True, padding=0)

        #AUDIO ANALYSIS
        page3 = Gtk.VBox()
        page3.set_border_width(3)
        notebook.append_page(page3, Gtk.Label('Audio Analysis'))
        
        self.audiodisplay = Gtk.VBox()
        self.audiodisplay.override_background_color(0, Gdk.RGBA(255,255,255,1))
        page3.add(self.audiodisplay)
        
        grid3 = Gtk.Grid()
        #grid3.set_halign(Gtk.Align.CENTER)
        grid3.set_hexpand(True)
        page3.add(grid3)
        b30 = Gtk.Button(label="Open Audio")
        b30.connect("clicked", self.open_audio_track)
        b31 = Gtk.Button(label="Profile Track")
        b31.connect("clicked", self.cm.audio_analyze)
        b33 = Gtk.Button(label="Classify Speech/Music/Silence")
        b33.connect("clicked", self.cm.classify_audio)
        b34 = Gtk.Button(label="Estimate Speech Emotion")
        b34.connect("clicked", self.cm.estimate_emotion)
        b35 = Gtk.Button(label="Estimate Split Edit")
        b35.connect("clicked", self.cm.estimate_split_edit)
#        completeAn = Gtk.RadioButton.new_with_label_from_widget(None,"Complete Analysis")
#        customAn = Gtk.RadioButton.new_with_label_from_widget(completeAn, "Custom Alaysis")
        options_box= Gtk.Grid()
        y = -1
        for x, label in enumerate(self.cm.aa.features):
            b = Gtk.CheckButton.new_with_label(label)
            b.connect("toggled", self.cm.aa.set_options, x)
            if x%2 == 0:
                y +=1
            options_box.attach(b, x%2, y, 1, 1)

        self.current_label2 = Gtk.Label()
        self.current_label2.set_markup("Edit Shot: "+"in Sequence: ")
        
        grid3.attach(b30, 0, 0, 5, 2)
        grid3.attach(self.buildSelector(), 0, 2, 5, 2)
        grid3.attach(self.current_label2, 0, 4, 5, 2)
        grid3.attach(b31, 6, 0, 5, 2)
        grid3.attach(options_box, 6, 2, 5, 5)
        grid3.attach(b33, 11, 0, 5, 2)
        grid3.attach(b34, 16, 0, 5, 2)
        grid3.attach(b35, 21, 0, 5, 2)
        
        #RESULTS PAGE
        page4 = Gtk.HBox()
        page4.set_border_width(3)
        page4.set_homogeneous(False)
        notebook.append_page(page4, Gtk.Label('Results'))
        
        databox = Gtk.VBox()
        databox.set_size_request(300, -1)
        page4.pack_start(databox, False, False, 3)
        displaybox = Gtk.VBox()
        displaybox.set_homogeneous(False)
        page4.pack_start(displaybox, True, True, 3)
        self.graph = Gtk.VBox()
        self.graph.override_background_color(0, Gdk.RGBA(255,255,255,1))
        self.graph.set_size_request(700, 600)
        displaybox.add(self.graph)
        
        get_res = Gtk.Button(label="Get Results")
        get_res.connect("clicked", self.get_results)
        load_data = Gtk.Button(label="Load Data")
        load_data.connect("clicked", self.cm.load_data)
        search_data = Gtk.Button(label="Search Data")
        search_data.connect("clicked", self.cm.search_data, "standard")
        search_tag_data  = Gtk.Button(label="Search Data for Tag")
        search_tag_data.connect("clicked", self.cm.search_data, "tag")
        adv_search = Gtk.Button(label="Advanced Search")
        adv_search.connect("clicked", self.cm.advanced_search)
        
        for b in [get_res, load_data, search_data, search_tag_data, adv_search]:
            databox.pack_start(b, False, False, 0)
        
        data_label = Gtk.Label()
        data_label.set_markup("<b>Data</b>")
        data_scroll = Gtk.ScrolledWindow()
        data_scroll.set_hexpand(False)
        data_scroll.set_vexpand(True)
        data_scroll.set_size_request(-1, 200)
        self.data_view = Gtk.TextView()
        self.data_view.set_editable(False)
        data_scroll.add(self.data_view)
        select_view = self.buildSelector("View", "Raw Data", "Normalized", "Histogram", view=True)
        trendlabel = Gtk.Label("Draw Trendline")
        self.trendswitch = Gtk.Switch()
        self.trendswitch.connect("notify::active", self.show_trendline)
        spinlabel = Gtk.Label("Set Trendline Degree")
        self.spin = Gtk.SpinButton.new_with_range(1.0, 100.0, 1.0)
        self.spin.set_digits(0)
        self.spin.set_numeric(True)
        self.spin.set_snap_to_ticks(True)
        self.spin.connect("value_changed", self.set_degree)
        
        databox.pack_start(Gtk.HSeparator(), False, False, 0)
        databox.pack_start(data_label, False, False, 1)
        databox.pack_start(data_scroll, True, True, 2)
        databox.pack_start(trendlabel, False, False, 1)
        databox.pack_start(self.trendswitch, False, False, 1)
        databox.pack_start(spinlabel, False, False, 0)
        databox.pack_start(self.spin, False, False, 0)
        databox.pack_start(select_view, False, False, 1)
        
        graph_box = Gtk.HBox()
        axes_box = Gtk.VBox()
        self.data_list = Gtk.ListStore(str, str)
        render_data = Gtk.CellRendererText()
        render_data.set_alignment(0.5, 0.5)
        self.data_combo1 = Gtk.ComboBox.new_with_model(self.data_list)
        self.data_combo2 = Gtk.ComboBox.new_with_model(self.data_list)
        self.data_combo3 = Gtk.ComboBox.new_with_model(self.data_list)
        self.data_combo4 = Gtk.ComboBox.new_with_model(self.data_list)
        for combo in [self.data_combo1, self.data_combo2, self.data_combo3, self.data_combo4]:
            combo.connect("changed", self.update_graph)
            combo.pack_start(render_data, True)
            combo.add_attribute(render_data, "text", 0)
        view_button = Gtk.Button(label="Draw Graph")
        view_button.connect("clicked", self.view_graph)
        
        for el in [self.data_combo1, self.data_combo2, self.data_combo3, self.data_combo4]:
            axes_box.pack_start(el, True, True, 1)
        graph_box.pack_start(axes_box, True, True, 1)
        graph_box.pack_start(view_button, False, False, 1)
        displaybox.pack_start(graph_box, True, True, 0)
        
        #SAVE PAGE
        page5 = Gtk.HBox()
        page5.set_homogeneous(False)
        page5.set_border_width(3)
        
        entrybox = Gtk.VBox()
        entrybox.set_border_width(6)
        page5.pack_start(entrybox, False, False, 0)
        bbox = Gtk.VBox()
        bbox.set_halign(Gtk.Align.CENTER)
        bbox.set_border_width(6)
        page5.pack_start(bbox, False, False, 0)
        
        authLab = Gtk.Label("Author: ")
        entrybox.pack_start(authLab, False, False, 0)
        self.authEntry = Gtk.Entry()
        entrybox.pack_start(self.authEntry, False, False, 0)
        companyLab = Gtk.Label("Company: ")
        entrybox.pack_start(companyLab, False, False, 0)
        self.companyEntry = Gtk.Entry()
        entrybox.pack_start(self.companyEntry, False, False, 0)
        commLab = Gtk.Label("Comment: ")
        entrybox.pack_start(commLab, False, False, 0)
        self.commEntry = Gtk.TextView()
        self.commEntry.set_size_request(900, 300)
        self.commEntry.override_background_color(0, Gdk.RGBA(255,255,255,1))
        entrybox.pack_start(self.commEntry, False, False, 0)
        tagLab = Gtk.Label("Tag: ")
        entrybox.pack_start(tagLab, False, False, 0)
        self.tagEntry = Gtk.TextView()
        self.tagEntry.set_size_request(900, 200)
        self.tagEntry.override_background_color(0, Gdk.RGBA(255,255,255,1))
        entrybox.pack_start(self.tagEntry, False, False, 0)
        
        upload = Gtk.Button(label="Upload")
        upload.set_size_request(300, 50)
        upload.connect("clicked", self.upload_data)
        save = Gtk.Button(label="Save")
        save.set_size_request(300, 50)
        save.connect("clicked", self.save_data)
        
        bbox.pack_start(upload, False, False, 10)
        bbox.pack_start(save, False, False, 10)
        notebook.append_page(page5, Gtk.Label('Share'))
        
        notebook.connect("switch-page", self.tab_switch)
        mainbox.pack_start(mb, False, True, 0)
        mainbox.pack_start(notebook, True, True, 0)
        
        self.clear_workset()
        self.add(mainbox)
        self.show_all()
        #keep hide some widgets
        self.shotbox.hide()
        self.seqbox.hide()
            
    def get_results(self, caller):
        self.data_list.append(["Empty", "empty"])
        for feat in self.cm.va.features:
            self.data_list.append(["Video: "+feat, feat])
        for feat in self.cm.va.nested_features:
            self.data_list.append(["Video: "+feat, feat])
        for feat in self.cm.aa.features:
            self.data_list.append(["Audio: "+feat, feat])
        for feat in self.cm.aa.nested_features:
            self.data_list.append(["Audio: "+feat, feat])
        
    def update_graph(self, caller):
        iter1 = self.data_combo1.get_active_iter()
        iter2 = self.data_combo2.get_active_iter()
        iter3 = self.data_combo3.get_active_iter()
        iter4 = self.data_combo4.get_active_iter()
        data_string, data, title = '', '', ''
        no_selection = True
        if self.fig == None:
            self.fig, self.ax = plt.subplots(1, 1)
            #self.legend, self.leg_names = [], []
            self.fig.subplots_adjust(left=0.04, bottom=0.12, right=0.99, top=0.97)
        for iter in iter1, iter2, iter3, iter4:
            if iter == None:
                continue
            text, name = self.data_list[iter][:]
            if name == "empty":
                continue
            no_selection = False
            dataFull, dataSeq, dataShot, type = self.cm.get_feature(name)
            sht = arange(0.0, float(self.cm.movie.n_shots), 1.0)
            seqt = []
            for seq in self.cm.seqs:
                seqt.append(seq.shots[1])
            movt = arange(0.0, float(self.cm.movie.n_shots), float(self.cm.movie.n_shots)-1)
            l = None
            if type == 'line':
                if self.view == 'raw':
                    if len(dataShot)>0:
                        l = self.ax.plot(sht, dataShot, lw=2, label=name)
                        data = dataShot
                    if len(dataSeq)>0:
                        l = self.ax.plot(seqt, dataSeq, lw=2, label=name)
                        data = dataSeq
                    if len(dataFull)==len(sht):
                        l = self.ax.plot(sht, dataFull, lw=2, label=name)
                        data = dataFull
                    if data == '':
                        data = 'Feature not extracted.'
                elif self.view == 'norm':
                    if len(dataShot)>0:
                        dataShot /= np.max(np.abs(dataShot))
                        l = self.ax.plot(sht, dataShot, lw=2, label=name)
                        data = dataShot
                    if len(dataSeq)>0:
                        dataSeq/=np.max(np.abs(dataSeq))
                        l = self.ax.plot(seqt, dataSeq, lw=2, label=name)
                        data = dataSeq
                    if len(dataFull)==len(sht):
                        dataFull/=np.max(np.abs(dataFull))
                        l = self.ax.plot(sht, dataFull, lw=2, label=name)
                        data = dataFull
                    if data == '':
                        data = 'Feature not extracted.'
                elif self.view == 'hist':
                    if len(dataShot)>0:
                        n, bins, l = self.ax.hist(dataShot, label=name, bins=50, rwidth=0.5)
                        data = n
                    if len(dataSeq)>0:
                        n, bins, l = self.ax.hist(dataSeq, label=name, bins=50, rwidth=0.5)
                        data = n
                    if len(dataFull)>0:
                        n, bins, l = self.ax.hist(dataFull, label=name, bins=50, rwidth=0.5)
                        data = n
                    if data == '':
                        data = 'Feature not extracted.'
                else:
                    data = "No data with the current options."
            elif type == 'multi':
                if self.view == 'raw' or self.view == 'norm':
                    if name == 'Color':
                        col = ['r', 'g', 'b']
                    else:
                        col = ['y', 'm', 'c', 'r', 'k', 'g']
                    if len(dataShot)>0:
                        bottoms = [0.0]*len(dataShot)
                        data = np.array(dataShot, dtype=float)
                        l = self.ax.bar(sht, data[:, 0], color=col[0])
                        for i in range(1, len(data[0])):
                            bottoms += data[:, i-1]
                            l = self.ax.bar(sht, data[:, i], bottom=bottoms, color=col[i%6])
                    if len(dataSeq)>0:
                        bottoms = [0.0]*len(dataSeq)
                        data = np.array(dataSeq, dtype=float)
                        l = self.ax.bar(seqt, data[:, 0], color=col[0])
                        for i in range(1, len(data[0])):
                            bottoms += data[:, i-1]
                            l = self.ax.bar(seqt, data[:, i], bottom=bottoms, color=col[i%6])
                    if len(dataFull)==len(sht):
                        bottoms = [0.0]*len(dataFull)
                        data = np.array(dataFull, dtype=float)
                        l = self.ax.bar(sht, data[:, 0], color=col[0])
                        for i in range(1, len(data[0])):
                            bottoms += data[:, i-1]
                            l = self.ax.bar(movt, data[:, i], bottom=bottoms, color=col[i%6])
                    if data == '':
                        data = 'Feature not extracted.'
                else:
                    self.data_view.get_buffer().set_text("No data with the current options.")
            elif type == 'scalar':
                if dataShot is not []:
                    self.data_view.get_buffer().set_text('\n\n'+name+':\n'+str(dataShot))
                    data = dataShot
                if dataSeq is not []:
                    self.data_view.get_buffer().set_text('\n\n'+name+':\n'+str(dataSeq))
                    data = dataSeq
                if dataFull is not []:
                    self.data_view.get_buffer().set_text('\n\n'+name+':\n'+str(dataFull))
                    data = dataFull
                if data == '':
                    data = 'Feature not extracted.'
            elif type == 'mat':
                if self.view == 'raw':
                    if len(dataShot)>0:
                        ds = np.array(dataShot)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        l = self.ax.plot(sht, val, lw=2, label=name)
                        data = dataShot
                    if len(dataSeq)>0:
                        ds = np.array(dataSeq)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        self.ax.plot(seqt, val, lw=2, label=name)
                        data = dataSeq
                    if len(dataFull)==len(sht):
                        ds = np.array(dataFull)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        self.ax.plot(sht, val, lw=2, label=name)
                        data = dataFull
                    if data == '':
                        data = 'Feature not extracted.'
                elif self.view == 'norm':
                    if len(dataShot)>0:
                        ds = np.array(dataShot)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        val /= np.max(val)
                        l = self.ax.plot(sht, val, lw=2, label=name)
                        data = dataShot
                    if len(dataSeq)>0:
                        ds = np.array(dataSeq)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        val /= np.max(val)
                        self.ax.plot(seqt, val, lw=2, label=name)
                        data = dataSeq
                    if len(dataFull)==len(sht):
                        ds = np.array(dataFull)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        val /= np.max(val)
                        self.ax.plot(sht, val, lw=2, label=name)
                        data = dataFull
                    if data == '':
                        data = 'Feature not extracted.'
                elif self.view == 'hist':
                    if len(dataShot)>0:
                        ds = np.array(dataShot)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        n, bins, l = self.ax.hist(val, label=name, rwidth=0.5)
                        data = n
                    if len(dataSeq)>0:
                        ds = np.array(dataSeq)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        n, bins, l = self.ax.hist(val, label=name, rwidth=0.5)
                        data = n
                    if len(dataFull)>0:
                        ds = np.array(dataFull)
                        val = np.array(ds[:, 0],dtype=float)
                        spec = ds[:, 1]
                        n, bins, l = self.ax.hist(val, label=name, rwidth=0.5)
                        data = n
                    if data == '':
                        data = 'Feature not extracted.'
                else:
                    data = "No data with the current options."
            else:
                self.data_view.get_buffer().set_text("No data with the current options.")
                continue
                
            if type != 'scalar':
                if l != None:
                    #self.legend.append(l)
                    #self.leg_names.append(name)
                    title = self.cm.movie.minfo.data['Title'].decode('utf8')
                    title += " ("+str(self.cm.movie.minfo.data['Year'])+")"
                if self.draw_trendline == True and not isinstance(data, str):
                    if self.view == 'hist':
                        step = bins[1]
                        x =arange(step/2,step*len(n),step)
                    elif len(dataShot)>0 or len(dataFull)>0:
                        x = sht
                    elif len(dataSeq)>0:
                        x = seqt
                    else:
                        continue
                    fit = polyfit(x, data, self.degree)
                    p = poly1d(fit)
                    self.ax.plot(x, p(x), lw=4)
                
            self.ax.minorticks_on()
            self.ax.get_xaxis().grid(True, which='both')
            feat_string = "\n"+name+":\n"+str(data)+'\n\n'
            replace_string = feat_string.replace('], ', '\n')
            if replace_string == feat_string:
                replace_string = feat_string.replace('), ', '\n')
                if replace_string == feat_string:
                    replace_string = feat_string.replace(', ', '\n')
            data_string += replace_string
        if no_selection == True:
            return
        if type in ['line', 'barstack'] and self.view in ['raw', 'norm']:
            self.ax.set_xlabel('Shots')
        else:
            self.ax.set_xlabel('Occurrence')
        self.data_view.get_buffer().set_text(data_string)
        self.ax.set_title(title)
        #self.fig.legend(self.legend, self.leg_names, 'right')
        leg= plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06), fancybox=True, shadow=True, ncol=4)
        leg.draggable()
        #draw vertical lines for seqs
        for seq in self.cm.seqs:
            self.ax.axvline(x=seq.shots[1], alpha=0.5)
        
    def view_graph(self, caller):
        if self.fc != None:
            self.graph.remove(self.fc)
            self.graph.remove(self.nt)
            self.fc.destroy()
            self.nt.destroy()
        if self.fig == None:
            return
        self.fc = FC(self.fig)
        self.graph.pack_start(self.fc, expand = True, fill=True, padding=0)
        self.nt = NT(self.fc, self.graph)
        self.graph.pack_start(self.nt, expand=False, fill=False, padding=0)
        self.fc.show_all()
        self.fig = None
    
    def change_view(self, caller, type):
        self.view = type
        self.update_graph(caller)
        self.view_graph(caller)
    
    def show_trendline(self, switch, gparam):
        if switch.get_active():
            self.draw_trendline = True
        else:
            self.draw_trendline = False
        self.update_graph(None)
        self.view_graph(None)
    
    def set_degree(self, caller):
        self.degree = self.spin.get_value_as_int()
        self.update_graph(caller)
        self.view_graph(caller)
        
    def row_selected(self, selection):
        model, row = selection.get_selected()
        if row != None:
            self.videoplayer2.seekpos(self, model[row][1])
            #self.videoplayer2.player.pause()
#            if model[row][5] == "Shots":
#                self.cm.current_shot = model[row][0] - 1
#                for seq in self.cm.seqs:
#                    if self.cm.current_shot in range(seq.shots[1], seq.shots[2]):
#                        self.cm.current_seq = seq.index
#            elif model[row][5] == "Sequences":
#                self.cm.current_seq = model[row][0] - 1
#                self.cm.current_shot = self.cm.seqs[self.cm.current_seq].shots[0].index
        
    def filter_func(self, model, iter, data):
        """Tests if the type in the row is the one in the filter"""
        if self.current_view is None or self.current_view == "None":
            return True
        else:
            return model[iter][6] == self.current_view

    def on_selection_button_clicked(self, widget):
        """Called on any of the filter button clicks"""
        #we set the current view filter to the button's label
        self.current_view = widget.get_label()
        if self.current_view == "Sequences":
            self.treeview.get_column(4).set_visible(True)
        if self.current_view == "Shots":
            self.treeview.get_column(4).set_visible(False)
        #we update the filter, which updates in turn the view
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.view_filter.refilter()
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
    
    def buildSelector(self,label="Work on:",lab1 = "Current Shot",lab2="Current Sequence",lab3="Full Title", view=False):
        separator = Gtk.HSeparator()
        selector_label = Gtk.Label(label)
        radio_ss_box = Gtk.VBox(spacing=2)
        button1 = Gtk.RadioButton.new_with_label_from_widget(None, lab1)
        radio_ss_box.pack_start(button1, False, False, 0)
        button2 = Gtk.RadioButton.new_with_label_from_widget(button1, lab2)
        radio_ss_box.pack_start(button2, False, False, 0)
        button3 = Gtk.RadioButton.new_with_label_from_widget(button1, lab3)
        radio_ss_box.pack_start(button3, False, False, 0)
        if view == False:
            button1.connect("toggled", self.set_workarea, "shot")
            button2.connect("toggled", self.set_workarea, "seq")
            button3.connect("toggled", self.set_workarea, "full")
        else:
            button1.connect("toggled", self.change_view, "raw")
            button2.connect("toggled", self.change_view, "norm")
            button3.connect("toggled", self.change_view, "hist")
        box = Gtk.VBox()
        for el in [separator, selector_label, radio_ss_box]:
            box.add(el)
        return box
        
    def BuildMenu(self):
        mb = Gtk.MenuBar()

        filemenu = Gtk.Menu()
        filem = Gtk.MenuItem("File")
        filem.set_submenu(filemenu)
       
        exit = Gtk.MenuItem("Exit")
        exit.connect("activate", Gtk.main_quit)
        filemenu.append(exit)
    
        editmenu = Gtk.Menu()
        editm = Gtk.MenuItem("Edit")
        editm.set_submenu(editmenu)
       
        pref = Gtk.MenuItem("Preferences")
        pref.connect("activate", Gtk.main_quit)
        editmenu.append(pref)
        
        viewmenu = Gtk.Menu()
        viewm = Gtk.MenuItem("View")
        viewm.set_submenu(viewmenu)
        
        fulls = Gtk.CheckMenuItem("Fullscreen")
        fulls.set_active(False)
        fulls.connect("activate",  self.maximize)
        viewmenu.append(fulls)
        
        toolsmenu = Gtk.Menu()
        toolsm = Gtk.MenuItem("Tools")
        toolsm.set_submenu(toolsmenu)
        
        ripup = Gtk.MenuItem("Full Analysis")
        ripup.connect("activate",  self.full_analysis)
        toolsmenu.append(ripup)
        
        helpmenu = Gtk.Menu()
        helpm = Gtk.MenuItem("Help")
        helpm.set_submenu(helpmenu)
        
        about = Gtk.MenuItem("About")
        about.connect("activate",  Gtk.main_quit)
        helpmenu.append(about)

        mb.append(filem)
        mb.append(editm)
        mb.append(viewm)
        mb.append(toolsm)
        mb.append(helpm)
        
        return mb
        
    def OpenFile(self, handler):
        if self.cm.movie.file != '':
            self.clear_workset()
        #FileChooser
        dialog = Gtk.FileChooserDialog("Please choose a Movie to analyze", self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
            t = magic.from_file(fname, mime=True)
            if re.search(r"video.*?",t) == None:
                self.message("You selected a nonvideo file")
                dialog.destroy()
                return
            else:
                dialog.destroy()
                #Initialize working set
                self.initialize_workset(fname)
        elif response == Gtk.ResponseType.CANCEL:
            self.message("No movie selected")
            dialog.destroy()
            return

    def open_audio_track(self, handler):
        if self.cm.aa.audio_path == '':
            self.message("Audio not extracted yet!")
            return
        fig = self.cm.aa.open_track()
        fc = FC(fig)
        self.audiodisplay.pack_start(fc, expand = True, fill=True, padding=0)
        nt = NT(fc, self.audiodisplay)
        self.audiodisplay.pack_start(nt, expand=False, fill=False, padding=0)
        fc.show_all()
        
    def tvsearch(self, handler):
        if self.cm.movie.minfo == None:
            return
        else:
            self.cm.movie.minfo.tv = True
            
    def movsearch(self, handler):
        if self.cm.movie.minfo == None:
            return
        else:
            self.cm.movie.minfo.tv = False
            
    def SearchMovieInfo(self, handler):
        self.cm.movie.minfo.find_title(self.searchentry.get_text())
        for id, result in enumerate(self.cm.movie.minfo.results):
            if result['kind'] == "movie":
                self.searchcombo.append(str(id), result['long imdb title'])
            elif result['kind'] == "tv series":
                self.searchcombo.append(str(id), result['long imdb title'])
    
    def GetMovieInfo(self, handler):
        selection = self.cm.movie.minfo.results[int(self.searchcombo.get_active_id())]
        self.cm.movie.minfo.assign_data(selection)
        self.movieinfo.set_markup(self.cm.movie.minfo.fill_label())
        
        link = urllib2.urlopen(self.cm.movie.minfo.data['Poster'])
        loader=GdkPixbuf.PixbufLoader()
        loader.write(link.read())
        loader.close()  
        buf = loader.get_pixbuf()
#        h = buf.get_height()
#        w = buf.get_width()
#        buf.scale_simple(200, (h/w)*200, GdkPixbuf.InterpType.BILINEAR)
        self.poster.set_from_pixbuf(buf)       
       
    def rip_source(self, handler):
        dialog = Gtk.FileChooserDialog("Please select the Disc to rip", self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            inpath = dialog.get_filename()
            dialog.destroy()
            if inpath == None:
                self.message("Operation failed!")
            else:
                dialog2 = Gtk.FileChooserDialog("Save ripped movie", self,
                    Gtk.FileChooserAction.SAVE,
                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
                dialog2.set_do_overwrite_confirmation(True)
                dialog2.set_create_folders(True)
                dialog2.set_current_name("MovieName.mkv")
                response = dialog2.run()
                
                if response == Gtk.ResponseType.OK:
                    outpath = dialog2.get_filename()
                    dialog2.destroy()
                    
                    if outpath.split(".")[1] != "mkv":
                        outpath += ".mkv"
                    
                    self.progbar.set_text("Encoding...")
                    self.progbar.pulse()
                    
                    self.proc = subprocess.Popen(("HandBrakeCLI","-i", inpath,"--stop-at","duration:00:01:00","--main-feature","-e",
                        "x264","--encoder-preset","faster","--encoder-tune",
                        "grain","-q","21","-E","copy","-o", outpath), 
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
                    while self.proc.poll() is None:
                        time.sleep(0.1)
                        self.progbar.pulse()
                        if Gtk.events_pending() is True:
                            Gtk.main_iteration()
                    
                    if self.proc.stdout.read()[-9:-3]=='exited':
                        self.initialize_workset(outpath)
                        self.progbar.set_text("Encoding done!")
                        self.progbar.set_fraction(1.0)
                else:
                    self.message("No destination selected")
                    dialog2.destroy()
            dialog.destroy()
        elif response == Gtk.ResponseType.CANCEL:
            self.message("No source selected")
            dialog.destroy()
        
    def cut_extract(self, handler):
        fname,  fext = os.path.splitext(self.cm.movie.file)
        vOutput = fname + '_cut' + fext
        ext = ".wav"
        aOutput = fname + '_audio' + ext
        if os.access(vOutput, os.F_OK):
            os.remove(vOutput)
        if os.access(aOutput, os.F_OK):
            os.remove(aOutput)
        start = self.start_time_entry.get_text()
        end = self.end_time_entry.get_text()
        if start != '' or end != '':
            if start == '':
                start = "00:00:00.00"
            if end == '':
                end = time_to_hmsf(self.cm.movie.length)
            subprocess.call(['ffmpeg', '-i', self.cm.movie.file, '-ss', start,
                        '-c', 'copy', '-to', end, vOutput])
            self.initialize_workset(vOutput)
        subprocess.call(['ffmpeg', '-i', self.cm.movie.file, '-vn', aOutput])
        self.cm.aa.audio_path = aOutput
    
    def tab_switch(self, notebook, page, page_num):
        if page_num == 0:
            self.videoplayer2.player.pause()
            self.videoplayer.player.set_mute(False)
            self.videoplayer.seekbar.set_value(self.videoplayer2.seekbar.get_value())
            self.videoplayer.player.pause()
        elif page_num == 1:
            self.videoplayer.player.pause()
            self.videoplayer2.player.set_mute(True)
            self.videoplayer2.seekbar.set_value(self.videoplayer.seekbar.get_value())
            self.videoplayer2.player.pause()
        else:
            pass

    def set_time(self, label):
        model, row = self.treeview.get_selection().get_selected()
        if row is not None:
            self.iter = row
        else:
            model = self.listore
        if self.iter is None:
            self.message("Add a blank row first!")
            return
        if label == "start":
            model[self.iter][1] = self.videoplayer2.time_label.get_text()
        if label == "end":
            model[self.iter][2] = self.videoplayer2.time_label.get_text()
            
    def add_title(self, renderer, path, text):
        if self.current_view == "Shots":
            return
        if self.current_view == "Sequences":
            index = int(path)+self.cm.movie.n_shots
            if self.listore[index][0] != 0:
                self.cm.seqs[int(path)].title = text
            row = self.listore.get_iter(Gtk.TreePath(index))
            self.listore.set_value(row, 4, text)
            
    def add_notes(self, renderer, path, text):
        #index = self.listore[int(path)][0] - 1
        if self.current_view == "Shots":
            self.cm.shots[int(path)].notes = text
            row = self.listore.get_iter(Gtk.TreePath(int(path)))
        if self.current_view == "Sequences":
            index = int(path)+self.cm.movie.n_shots
            if self.listore[index][0] != 0:
                self.cm.seqs[int(path)].notes = text
            row = self.listore.get_iter(Gtk.TreePath(index))
        self.listore.set_value(row, 5, text)
    
    def update_marker(self):
        self.videoplayer2.seekbar.clear_marks()
        for shot in self.cm.shots:
            self.videoplayer2.seekbar.add_mark(s_to_frames(shot.startns, nanos=True), Gtk.PositionType.TOP, None)
        for seq in self.cm.seqs:
            self.videoplayer2.seekbar.add_mark(s_to_frames(seq.startns, nanos=True), Gtk.PositionType.BOTTOM, None)
    
    def tree_update(self):
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.listore.clear()
        for el in self.cm.shots:
            if len(el.vid_features) == 0:
                self.listore.append([el.index, el.start, el.end, el.length, "", el.notes, "Shots"])
            else:
                self.listore.append([el.index, el.start, el.end, el.length, "", el.notes, "Shots"])
        for el in self.cm.seqs:
            self.listore.append([el.index, el.start, el.end, el.duration, el.title, el.notes, "Sequences"])
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        
    def update_position(self):
        videopos = hmsf_to_time(self.videoplayer2.time_label.get_text(), nanos=True)
        for shot in self.cm.shots:
            if videopos >= shot.startns:
                if videopos < shot.endns + framestep:
                    self.cm.current_shot = shot.index - 1
                    break
        for seq in self.cm.seqs:
            if videopos >= seq.startns:
                if videopos < seq.endns + framestep:
                    self.cm.current_seq = seq.index - 1
                    break
        self.current_label.set_markup("Editing Shot: <b>"+ str(self.cm.current_shot+1) + 
                                "</b> in Sequence: <b>"+ str(self.cm.current_seq+1) +"</b>")
        self.current_label2.set_markup("Editing Shot: <b>"+ str(self.cm.current_shot+1) + 
                                "</b> in Sequence: <b>"+ str(self.cm.current_seq+1) +"</b>")
        return videopos

    def shot_scale(self, handler):
        self.cm.shot_scale()
        #self.treeview.get_column(7).set_visible(True)
        #self.treeview.get_column(8).set_visible(True)
        self.tree_update()
    
    def shot_detect(self, handler):
        #reset all fields
        self.cm.shots = []
        self.cm.seqs = []
        
        th = self.thres_scale.get_value()
        black_dur = self.blackdur_scale.get_value()
        pix_th = self.pix_thres.get_value()
        
        success = self.cm.shot_detect(th, black_dur, pix_th)
        if success == False:
            self.message("Please rename your file without special characters.")
        else:
            self.tree_update()
            self.update_marker()
            
    def edit_shots(self, toggle):
        self.current_view = "Shots"
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.view_filter.refilter()
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        
        if toggle.get_active():
            self.shotbox.show()
        else:
            self.shotbox.hide()
            
    def edit_sequences(self, toggle):
        self.current_view = "Sequences"
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.view_filter.refilter()
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        
        if toggle.get_active():
            self.seqbox.show()
            self.treeview.get_column(4).set_visible(True)
        else:
            self.seqbox.hide()
        
    def shot_prev(self):
        #self.update_position()
        if self.cm.current_shot != 0:
            #self.cm.current_shot -=1
            self.videoplayer2.seekpos(self, self.cm.shots[self.cm.current_shot-1].start)
    
    def shot_next(self):
        #self.update_position()
        if (self.cm.current_shot+1) != len(self.cm.shots):
            #self.cm.current_shot +=1
            self.videoplayer2.seekpos(self, self.cm.shots[self.cm.current_shot+1].start)
    
    def shot_add(self):
        newcut = self.videoplayer2.player.get_pipeline().query_position(Gst.Format.TIME)[1]
        cur = self.cm.current_shot
        start = self.cm.shots[cur].startns
        end = self.cm.shots[cur].endns
        if newcut not in (start, end):
            del self.cm.shots[cur]
            self.cm.shots.insert(cur, Shot(cur+2, newcut+framestep, end))
            self.cm.shots.insert(cur, Shot(cur+1, start, newcut))
            self.cm.movie.n_shots += 1
        else:
            return
            
        for el in self.cm.shots[self.cm.current_shot+2:]:
            el.index += 1
        self.tree_update()
        self.videoplayer2.seekbar.add_mark(s_to_frames(newcut+framestep, nanos=True), Gtk.PositionType.TOP, None)
        
    def shot_fix(self):
        fix = self.videoplayer2.player.get_pipeline().query_position(Gst.Format.TIME)[1]
        model, iter = self.treeview.get_selection().get_selected()
        cur = model[iter][0] - 1
        if fix != self.cm.shots[cur].startns:
            end = self.cm.shots[cur].endns
            start = self.cm.shots[cur-1].startns
            del self.cm.shots[cur]
            del self.cm.shots[cur-1]
            self.cm.shots.insert(cur-1, Shot(cur+1, fix, end))
            self.cm.shots.insert(cur-1, Shot(cur, start, fix-framestep))
            self.tree_update()
            self.update_marker()
        
    def shot_del(self):
        del self.cm.shots[self.cm.current_shot]
        self.cm.movie.n_shots -= 1
        for el in self.cm.shots[self.cm.current_shot:]:
            el.index -= 1
        self.tree_update()
        self.update_marker()
#        check on time unassigned at any shot
#        if self.cm.current_shot-1 >= 0:
#            if self.cm.shots[self.cm.current_shot-1].endns 
            
    def seq_prev(self):
        if self.cm.current_seq not in (-1, 0):
            #self.cm.current_seq -=1
            self.videoplayer2.seekpos(self, self.cm.seqs[self.cm.current_seq-1].start)
    
    def seq_next(self):
        if (self.cm.current_seq+1) < self.cm.movie.n_seqs:
            #self.cm.current_seq +=1
            self.videoplayer2.seekpos(self, self.cm.seqs[self.cm.current_seq+1].start)

    def add_blank_seq_row(self):
        self.iter = self.listore.append([0, "", "", "", "", "", "Sequences"])
        
    def seq_add(self):
        if self.cm.movie.file == '' and self.cm.movie.n_shots + self.cm.movie.n_seqs == len(self.listore):
            self.message("Add a blank row first!")
            return
        
        index = self.cm.current_seq + 2
        start = self.listore[self.iter][1]
        end = self.listore[self.iter][2]
        title = self.listore[self.iter][4]
        notes = self.listore[self.iter][5]
        
        if self.cm.current_seq == -1 or hmsf_to_time(start)>hmsf_to_time(self.cm.seqs[self.cm.current_seq].end):
            self.cm.seqs.append(Sequence(index, title, start, end, notes, self.cm.shots))
            self.cm.movie.n_seqs +=1
            self.cm.current_seq +=1
            el = self.cm.seqs[self.cm.current_seq]
            self.listore.append([el.index, el.start, el.end, el.duration, el.title, el.notes, 'Sequences'])
        else:
            self.message("Start time must be after the ending of previous sequence.")
        
        self.tree_update()
        self.videoplayer2.seekbar.add_mark(s_to_frames(hmsf_to_time(start)), Gtk.PositionType.BOTTOM, None)
        self.iter = None

    def seq_fix(self):
        model, iter = self.treeview.get_selection().get_selected()
        if self.cm.movie.file != '' and self.cm.movie.n_shots != len(self.listore) and iter is not None:
            cur = model[iter][0] - 1
            index = cur + self.cm.movie.n_shots
            title = self.listore[index][4]
            start = self.listore[index][1]
            end = self.listore[index][2]
            notes = self.listore[index][5]
            del self.cm.seqs[cur]
            self.cm.seqs.insert(cur, Sequence(cur+1, title, start, end, notes, self.cm.shots))
            self.tree_update()
            self.update_marker()
            
    def seq_del(self):
        if self.cm.movie.file != '' and self.cm.movie.n_shots != len(self.listore):
            del self.cm.seqs[self.cm.current_seq]
            self.cm.movie.n_seqs -=1
            for el in self.cm.seqs[self.cm.current_seq:]:
                el.index -= 1
            self.tree_update()
            self.update_marker()
        
    def acquire_frame(self, handler):
        #JPG format
        npos = self.videoplayer2.player.get_position()
        pos = time_to_hmsf(npos, nanos=True, string=True)
        spos = pos.split(":")[0] + "-" + pos.split(":")[1] + "-" + pos.split(":")[2].split(".")[0] + "-" + pos.split(".")[1]
        output = 'snap'+ spos +'.jpg'
        #ss after -i for accuracy, but it takes much more time
        subprocess.call(['ffmpeg', '-i', self.cm.movie.file, '-ss', pos,
                                    '-f', 'image2', '-frames:v', '1', output])
        
    def full_analysis(self, handler):
        self.cm.workon='full'
        self.cm.va.options = [True]*len(self.cm.va.features)
        self.cm.aa.options = [True]*len(self.cm.aa.features)
        #Video
        print("Full Analysis")
        self.shot_detect(None)
        print("done Shot Detect")
        self.shot_scale(None)
        print("done Shot Scale")
        self.cm.charachters_movement(None)
        print("done Charachters Movement")
        self.cm.camera_movement(None)
        print("Done Camera Movement")
        self.cm.shannon_entropy(None)
        print("done Shannon Entropy")
        self.cm.get_contrast_brightness(None)
        print("done Contrast Brightness Saturation")
        self.cm.get_color(None)
        print("done Get Color")
        self.cm.video_analyze(None)
        print("done Video Analyze")
        #Audio
        self.open_audio_track(None)
        print("Audio Track Opened")
        self.cm.audio_analyze(None)
        print("done Audio Analysis")
        self.cm.classify_audio(None)
        print("done Classify Audio")
        self.cm.estimate_emotion(None)
        print("done Speech Emotion")
        self.cm.estimate_split_edit(None)
        print("done Split Edit")
        print("Analysis Complete!")
        
        self.message("Analysis complete!\nGo to Results tab.")
        
    def initialize_workset(self, fname):
        global fps,  framestep
        self.cm.movie.file = fname
        self.videoplayer.player.set_uri("file://" + fname)
        self.videoplayer2.player.set_uri("file://" + fname)
        self.cm.movie.finfo.file = fname
        self.cm.movie.finfo.assign_data()
        fps = self.cm.movie.finfo.data['Framerate Num']
        framestep = frames_to_s(1, nanos=True)
        self.cm.movie.framecount = self.cm.movie.finfo.data['Frame Count']
        self.cm.movie.length = frames_to_s(self.cm.movie.framecount, nanos=False)
        self.fileinfo.set_markup(self.cm.movie.finfo.fill_label())
        self.videoplayer.seekbar.set_range(0.0, self.cm.movie.framecount)
        self.videoplayer.seekbar.set_increments(1.0/fps, 1.0/fps)
        self.videoplayer.out = self.cm.movie.framecount
        self.videoplayer2.seekbar.set_range(0.0, self.cm.movie.framecount)
        self.videoplayer2.seekbar.set_increments(1.0/fps, 1.0/fps)
        self.videoplayer2.out = self.cm.movie.framecount
        self.videoplayer2.player.set_mute(True)
        self.videoplayer.pause()
        self.iter = None
    
    def clear_workset(self):
        self.cm.movie.file = ''
        self.videoplayer.player.set_uri("file://")
        self.videoplayer2.player.set_uri("file://")
        self.cm.movie.finfo.file = ''
        self.fileinfo.set_markup("<b>Movie not loaded!\nOpen a file or rip your disc.</b>")
        self.movieinfo.set_markup("<b>No Movie Info collected.</b>")
        self.videoplayer.seekbar.set_range(0, 0)
        self.videoplayer2.seekbar.set_range(0, 0)
        self.progbar.set_fraction(0)
        self.progbar.set_text("0%")
        self.iter = None
        
    def set_workarea(self, handler, label):
        self.cm.workon = label
        
    def terminate_proc(self):
        if not hasattr(self.cm, "proc"):
            return
        self.proc.kill()
        self.message("The encode is not complete.\nDon't use this file for analysis.")
        time.sleep(1)
        self.clear_workset()
    
    def message(self, text):
        msg = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK, text)
        msg.run()
        msg.destroy()
        return
    
    def upload_data(self, caller):
        filename = self.save_data(None)
        
    def save_data(self, caller):
        inputData = [self.authEntry.get_text(), self.companyEntry.get_text()]
        start = self.commEntry.get_buffer().get_start_iter()
        end = self.commEntry.get_buffer().get_end_iter()
        comment = self.commEntry.get_buffer().get_text(start, end, False)
        start = self.tagEntry.get_buffer().get_start_iter()
        end = self.tagEntry.get_buffer().get_end_iter()
        tags = self.tagEntry.get_buffer().get_text(start, end, False)
        inputData.append(comment, tags)
        filename = self.cm.movie.minfo.data['Title']+'.json'
        
        if caller != None:
            dialog = Gtk.FileChooserDialog("Please choose a folder", self,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 "Select", Gtk.ResponseType.OK))
            dialog.set_default_size(800, 400)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename()+filename
            dialog.destroy()
        
        self.cm.save_data(filename, inputData)
        return filename
        
if __name__ == '__main__':
#    x11 = CDLL("libX11.so")
#    x11.XInitThreads()
    Gdk.threads_init()
    Gst.init(None)
    win = CmGUI()  
    Gtk.main()
    

