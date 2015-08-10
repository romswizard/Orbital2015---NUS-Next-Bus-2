#kivy.require("1.8.0")

#Kivy Library
from kivy.app import App 
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivy.logger import Logger
from kivy.uix.popup import Popup
from kivy import platform
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label

#Python Native
from functools import partial
from threading import Thread
import datetime
import re

#Imported Source Files
import datamall
import datadb
import netcheck
import toast
from facebook import Facebook #jnius Interpreter

#Default <Bus Service ended> text
busServiceEnded = 'Not Available'
#Bus Timing Update Frequency (seconds)
_updateFrequency = 5
#Facebook APP ID
FACEBOOK_APP_ID = '904238149623014'


class BusInfo(FloatLayout):
	def __init__(self, **kwargs):
		super(BusInfo, self).__init__(**kwargs)

class DummyScrollEffect(ScrollEffect):
	#ScrollEffect: Does not allow scrolling beyond the ScrollView boundaries.
	#When scrolling would exceed the bounds of the ScrollView, it uses a ScrollEffect to handle the overscroll. These effects can perform actions like bouncing back, changing opacity, or simply preventing scrolling beyond the normal boundaries. Note that complex effects may perform many computations, which can be slow on weaker hardware.
	#You can also create your own scroll effect by subclassing one of these, then pass it as the effect_cls in the same way.
	pass

class DateTimeInfo():
	def getTimeNow(self):
		#Returns local time
		return datetime.datetime.now().strftime("%H:%M:%S")
	def getDateNow(self):
		#Returns local time
		return datetime.datetime.now().strftime("%Y-%m-%d") 
	def getUTCTime(self):
		#Returns UTC Time. To calculate difference between arrival and current timings
		return datetime.datetime.utcnow().strftime("%H:%M:%S")


class SearchBus(Screen):
	current_labels=[]
	loading_widget_collector=[]
	listview_widget_collector=[]
	isScreenDisabled = BooleanProperty(False)

	scrolleffect = DummyScrollEffect

	def on_isScreenDisabled(self, *args):
		if self.isScreenDisabled:
			self.ids['searchbusscreen_floatlayout'].disabled = True
		else:
			self.ids['searchbusscreen_floatlayout'].disabled = False

	def expand_menu(self):
		#Removes active header
		header_label = self.ids['searchbus1']
		header_placeholder = self.ids['header_placeholder']
		header_searchbutton = self.ids['search_button_grid']
		self.header_active = [header_label, header_placeholder, header_searchbutton]
		
		for each_header_widget in self.header_active:
			self.ids['header'].remove_widget(each_header_widget) 

		#Changes to active input menu
		self.header_back_button = Button(
			to_parent=True,
			size_hint=(0.1,1),
			background_normal='data/return.png',
			background_down='data/return_down.png'
			)
		self.header_back_button.bind(on_release=self.contract_menu)

		#Text Input Field Behaviour
		self.header_textinput = TextInput(
			to_parent=True,
			size_hint=(0.9,1),
			pos_hint={"top":1,"left":1},
			height='120dp', 
			multiline=False, 
			cursor_blink=True,
			cursor_color=(1,1,1,1),
			foreground_color=(1,1,1,1),
			hint_text_color=(1,1,1,0.7),
			hint_text='Search a bus stop number',
			font_size='24sp',
			background_active='data/text_input_focus.png',
			background_normal='data/text_input.png'
			)
		#on_text behaviour
		self.header_textinput.bind(text=self.on_text)
		#on validate key behaviour
		self.header_textinput.bind(on_text_validate=self.start_search)

		self.header_inactive = [self.header_back_button, self.header_textinput]

		for each_header_widget in self.header_inactive:
			self.ids['header'].add_widget(each_header_widget)

		#Sets focus to the text input (updates in the next frame, or it will not work. This is a getaround)
		Clock.schedule_once(self.focus_on_textinput,0)

	def contract_menu(self, *args):
		#removes inactive header
		for each_header_widget in self.header_inactive:
			self.ids['header'].remove_widget(each_header_widget)

		#removes the listview if exists
		if self.listview_widget_collector:
			for each_listview_widget in self.listview_widget_collector:
				self.ids['searchbusscreen_floatlayout'].remove_widget(self.listview_widget_collector.pop()) 
				
		#restores active header
		for each_header_widget in self.header_active:
			self.ids['header'].add_widget(each_header_widget)

	def focus_on_textinput(self, *args):
		self.header_textinput.focus = True

	#Suggested Bus stops
	def on_text(self, *args):
		#get text field text
		text_input_value = self.header_textinput.text
		#once user has type 3 letters and more, start substring search
		if len(text_input_value)>2:

			#if previous listview exists, remove it
			self.closeListView()

			#start search, put the response data in a list adapter
			suggestions = app.datamall_bus_stop.busnamesubstringSearch(text_input_value)
			
			#ListitemButton Behaviour
			args_converter = lambda row_index, rec: {
			'text':rec['text'],
			'size_hint':(None,None),
			'height': '50dp',
			'width': self.header_textinput.width
			}

			suggestion_listadapter = ListAdapter(
				data=suggestions,
				args_converter=args_converter,
				selection_mode='multiple',
				selection_limit=1,
				allow_empty_selection=True,
				cls=ListItemButton
				)
			#binds each listview button to the autofill function
			suggestion_listadapter.bind(on_selection_change=self.selection_change)
			
			#Logger.info("heightheight"+str(dp(60)))
			#Logger.info("heightheight"+str(float(dp(50)*len(suggestions)/self.height)))

			self.suggestion_listview = ListView(
				adapter=suggestion_listadapter,
				size_hint_y=(float(dp(50)*len(suggestions)/self.height)) if (float(dp(50)*len(suggestions)/self.height))<0.4 else 0.4,
				width=self.header_textinput.width,
				pos_hint={"top":(self.height-self.header_textinput.height*1.3)/self.height},
				x=self.header_textinput.x
				)

			#The container is a GridLayout widget held within a ScrollView widget.
			#So we are giving the ScrollViewParent a custom scroll effect
			#ListView >> ScrollView >> GridLayout
			#effect_cls is an ObjectProperty and defaults to DampedScrollEffect.
			self.suggestion_listview.container.parent.effect_cls = self.scrolleffect

			#Timeout allowed to trigger the scroll_distance, in milliseconds. If the user has not moved scroll_distance within the timeout, the scrolling will be disabled, and the touch event will go to the children.
			self.suggestion_listview.container.parent.scroll_distance = 10
			self.suggestion_listview.container.parent.scroll_timeout = 	1000

			self.listview_widget_collector.append(self.suggestion_listview)
			self.ids['searchbusscreen_floatlayout'].add_widget(self.suggestion_listview)

		else:
			#User is deleting his input, so naturally, we shall close the listview (if it exists)
			self.closeListView()

	#user touches a suggestion
	def selection_change(self, *args):
		selected_item = args[0].selection[0]
		#Logger.info("busstopselection"+str(selected_item.text))
		
		#On First Selection or when the textinput is not the same as the option selected
		#Auto fills the text input widget
		if selected_item.text != self.header_textinput.text:
			self.header_textinput.text = selected_item.text

		#On Second Selection + color change
		#If text field is the same as the text in the selection, close the listview and start the search
		else:
			self.start_search()


	def getBusStopNamefromCode(self, _busstopcode):
		return app.datamall_bus_stop.getBusStopName(_busstopcode)

	def closeListView(self):
		#close the suggestion listview (if any)
		if self.listview_widget_collector:
			for each_listview in self.listview_widget_collector:
				self.ids['searchbusscreen_floatlayout'].remove_widget(self.listview_widget_collector.pop())

	#search text input accepts strings and numbers
	def start_search(self, *args):
		#if listview is active, close it
		self.closeListView()
		self.getUserInput()
		self.contract_menu()
		self.searchUserInput()

	#Gets user input from the text fields busStopNoInput & busNoInput
	def getUserInput(self, *args):
		self._busnoinput = ''

		#If search value is a number
		if self.header_textinput.text.isdigit():
			self._busstopnoinput = self.header_textinput.text
		#if the string is not a digit
		else:
			response_busstopcode = app.datamall_bus_stop.searchBusStopCode(self.header_textinput.text)
			#if response is not None
			if response_busstopcode:
				self._busstopnoinput = response_busstopcode
			#not a valid bus stop. Are we gonna let it carry on first?
			else:
				self._busstopnoinput = self.header_textinput.text


	def searchUserInput(self, *args):
		#Instantiates a connection to datamall API
		#Bus 911 @ a working bus stop: 46429,911/83139
		app._toast('Searching for Bus Stop {}'.format(self._busstopnoinput))

		#Gets list of all bus services in operation	
		allbuses_instance = datamall.BusInfo(self._busstopnoinput, self._busnoinput)
		
		#Valid Bus Stop Check?
		if allbuses_instance.response.status == 200:
	
			self.busservices = allbuses_instance.getallServices()

			#Removes existing labels, (if any)
			if self.current_labels:
				for _eachbuswidget in self.current_labels:
					self.ids['searchbusscreen_gridlayout'].remove_widget(_eachbuswidget)

			#Displays Loading widget
			loading_widget = LoadingWidget()
			self.ids['searchscreen_main_body'].add_widget(loading_widget)
			self.loading_widget_collector.append(loading_widget)

			#Disables main body
			self.isScreenDisabled = True

			#Get user preferences (saved buses)>>UI remains responsive now. Widgets can only be created after records are retrieved
			#Retrieval of records allow for Checkboxes to be created with user's preference shown
			self.retrievePreferredStops()

		#invalid bus stop id or when all bus services have ceased operation
		else:
			app._toast('Invalid Bus Stop!')


	def create_bus_instance_widgets(self, *args):
		#Stop displaying loading widget
		if self.loading_widget_collector:
			for loading_widget in self.loading_widget_collector:
				self.ids['searchscreen_main_body'].remove_widget(self.loading_widget_collector.pop())

		#creates new labels and appends ref
		for (eachbus) in self.busservices:
			#Creates an EachBus instance for eachbus & Adds the Label instance to root. One bus service to one EachBus() instance
			self.each_bus_instance = EachBus(self._busstopnoinput, eachbus['ServiceNo'])			
			self.eachbuswidget = self.each_bus_instance.getEachBusGridLayoutWidget()

			#append to the current_labels list
			self.current_labels.append(self.eachbuswidget)

			#append to the Parent Layout
			self.ids['searchbusscreen_gridlayout'].add_widget(self.eachbuswidget)
		
			#Checkbox::Binds the Boolean Property 'active' to self.on_checkbox_active()		
			self.each_bus_instance.getLabels()[3].bind(active=partial(self.on_checkbox_active, self.each_bus_instance.getServiceNo(), self.each_bus_instance.getBusStopID(), self.each_bus_instance.getLabels()[3]))

		#Each bus's canvas instructions for loading texture
		for _eachbuswidget in self.current_labels:
			with _eachbuswidget.canvas.before:
				#Tints and opacity can be achieved!
				_eachbuswidget.canvas.opacity = 0.9
				thiscanvasrect = Rectangle(pos=_eachbuswidget.pos, size=_eachbuswidget.size, source='data/bg/each_label.png')

				#http://kivy.org/planet/2014/10/updating-canvas-instructions-declared-in%C2%A0python/
				#on pos or size change of the GridLayout, update the position of the canvas as well!
				_eachbuswidget.bind(pos=partial(self.update_label_canvas, _eachbuswidget, thiscanvasrect), size=partial(self.update_label_canvas, _eachbuswidget, thiscanvasrect))

		#enables main body again
		self.isScreenDisabled = False

		'''
		#show current bus stop name in search
		busstopnamelabel = Label(
			text=self.this_busstopname,
			size_hint=(1,None),
			height='60dp',
			font_size='16sp'
			)

		self.current_labels.append(busstopnamelabel)
		self.ids['searchbusscreen_gridlayout'].add_widget(busstopnamelabel)
		'''

	def update_label_canvas(self, thisbuswidget, thiscanvasrect, *args):
		thiscanvasrect.pos = thisbuswidget.pos
		thiscanvasrect.size = thisbuswidget.size

	def retrievePreferredStops(self, *args):
		#If records not retrieved
		if not app.isRecordRetrieved:
			#Get user preferences (saved buses). Will exit thread if user is not logged in
			thread1 = Thread(target=app.getUserSaveBusRecords,args=()).start()
		#thread2 starts even before thread 1 is done (if thread1 is executed)
		thread2 = Thread(target=self.check_UserSaveBusRecords_if_exists,args=()).start()


	def check_UserSaveBusRecords_if_exists(self,*args):
		#Still retrieving records (only if logged in)
		if app._facebookid:
			while not app.isRecordRetrieved:
				time.sleep(1)
		#Retrieval done
		Clock.schedule_once(self.create_bus_instance_widgets, 0)


	def on_checkbox_active(self, _serviceno, _busstopid, _labelref, *args):
		#If logged in and has checked this bus		
		if app._facebookid and _labelref.active == True:
			#updates mySQL DB
			thread = Thread(target=self.createUserSaveBusRecords, args=(_serviceno, _busstopid, _labelref))
			thread.start()
			app.all_saved_busstopNo.append(_busstopid)
			app.all_saved_busno.append(_serviceno)
			app._toast('Saved!')
		#If logged in and has unchecked this bus
		elif app._facebookid and not _labelref.active == True:
			#updates mySQL DB
			app.all_saved_busstopNo.remove(_busstopid)
			app.all_saved_busno.remove(_serviceno)
			app._toast('Deleted!')
		elif not app._facebookid:
			_labelref.active = False
			app._toast('Please login into Facebook first')

	def createUserSaveBusRecords(self, _serviceno, _busstopid, _labelref):
		#if the SaveBusRecords does not exist, response code of GET request is != 200
		#Create a new UserSaveBusRecords
		response = datadb.PostDBInfo().createUserSaveBusRecords(_serviceno, _busstopid, app._facebookid)
		Logger.info('Saving the User\'s preference' + str(response))

	def deleteUserSaveBusRecords(self, _serviceno, _busstopid, _labelref, *args):
		#Deletes a UserSaveBusRecord
		response = datadb.DeleteDBInfo().deleteUserSavebusRecords(_serviceno, _busstopid, app._facebookid)
		#Logger.info('Deleting the User\'s preference' + str(response))

		#We have a response from the DELETE request
		delete_complete_status_code = response.status_code
		self.deleteCompleted(delete_complete_status_code)
	
	def saveCompleted(self, save_complete_status_code, *args):
		Clock.schedule_once(partial(self.showSaveCompletedToast, save_complete_status_code), 0)
	
	def showSaveCompletedToast(self, save_complete_status_code, *args):
		#Response for POST is 200
		if save_complete_status_code==200:
			#Remove Saving now widget
			if self.loading_widget_collector:
				for each_saving_widget in self.loading_widget_collector:
					self.ids['searchscreen_main_body'].remove_widget(self.loading_widget_collector.pop())
			app._toast('Saved!')
			self.isScreenDisabled = False
		else:
			app._toast('Can\'t save! Error Code: {}'.format(str(self.save_complete)))

	def deleteCompleted(self, delete_complete_status_code, *args):
		Clock.schedule_once(partial(self.showDeleteCompletedToast, delete_complete_status_code), 0)

	def showDeleteCompletedToast(self, delete_complete_status_code, *args):
		#Response for DELETE is 200
		if delete_complete_status_code==200:
			#Remove Deleting now widget
			if self.loading_widget_collector:
				#Updates widget Label
				for each_deleting_widget in self.loading_widget_collector:
					self.ids['searchscreen_main_body'].remove_widget(self.loading_widget_collector.pop())
			app._toast('Deleted!')
			self.isScreenDisabled = False
		else:
			app._toast('Can\'t delete! Error Code: {}'.format(str(self.delete_complete)))

	
#Contains the instance for Each bus
class EachBus():
	#Creates all the labels upon initialization
	def __init__(self, _busstopid, _serviceno, row):
		self._busstopid = _busstopid
		self._serviceno = _serviceno
		#creates the nextbustime instance
		self.nextbustimelabel = Label(font_size=22, text=self.getNextBusTime(), size_hint=(0.3,0.05), pos_hint={"x":0.2, "y":(0.75-row*0.1)})
		self.nextbusloadlabel = Label(font_size=22, text=self.getNextBusLoad(), size_hint=(0.3,0.05), pos_hint={"x":0.2, "y":(0.70-row*0.1)})
		#creates the subsequentbustime instance
		self.subsequentbustimelabel = Label(font_size=22, text=self.getSubsequentBusTime(), size_hint=(0.3,0.05), pos_hint={"x":0.5, "y":(0.75-row*0.1)})
		self.subsequentbusloadlabel = Label(font_size=22, text=self.getSubsequentBusLoad(), size_hint=(0.3,0.05), pos_hint={"x":0.5, "y":(0.70-row*0.1)})
		#Creates the service number instance
		self.servicenolabel = Label(font_size=22, text=self.getServiceNo(), size_hint=(0.2,0.05), pos_hint={"x":0, "y":(0.75-row*0.1)})
		#Creates the save bus checkbox
		saved_status = False
		#checks if the user has saved this bus 
		if app.all_saved_busstopNo and app.all_saved_busno:
			if (self._busstopid,self._serviceno) in zip(app.all_saved_busstopNo, app.all_saved_busno):
				saved_status=True
		self.savebuscheckbox = CheckBox(size_hint=(0.1,0.1), pos_hint={"x":0.85, "y":(0.725-row*0.1)}, active=saved_status)


	def getNextBusTime(self):
		try:
			#Creates a GET request instance
			self.busInstance = datamall.BusInfo(self._busstopid,self._serviceno)
			self.busInstance.scrapeBusInfo()
			dateTime = self.busInstance.getNextTiming()
			grabTime = re.findall('[0-9]+\D[0-9]+\D[0-9]+',dateTime)
			#grabTime[0]==date #grabTime[1]==time(UTC)
			timedelta = datetime.datetime.strptime(grabTime[1],"%H:%M:%S") - datetime.datetime.strptime(DateTimeInfo().getUTCTime(),"%H:%M:%S")
			timeLeft = re.split(r'\D',str(timedelta))
			if dateTime:	
				#timeLeft[0] can return null at times
				if not (timeLeft[0]):
					timeLeft[0]=0	
				return '%s MINUTES %s SECONDS' %(str(int(timeLeft[0])*60+int(timeLeft[1])),timeLeft[2])
		except TypeError:
			return busServiceEnded

	def getSubsequentBusTime(self):
		try:
			#Creates a GET request instance
			self.busInstance = datamall.BusInfo(self._busstopid,self._serviceno)
			self.busInstance.scrapeBusInfo()
			dateTime = self.busInstance.getSubsequentTiming()
			grabTime = re.findall('[0-9]+\D[0-9]+\D[0-9]+',dateTime)
			#grabTime[0]==date #grabTime[1]==time(UTC)
			timedelta = datetime.datetime.strptime(grabTime[1],"%H:%M:%S") - datetime.datetime.strptime(DateTimeInfo().getUTCTime(),"%H:%M:%S")
			timeLeft = re.split(r'\D',str(timedelta))
			if dateTime:
				#timeLeft[0] can return null at times
				if not (timeLeft[0]):
					timeLeft[0]=0	
				return '%s MINUTES %s SECONDS' %(str(int(timeLeft[0])*60+int(timeLeft[1])),timeLeft[2])
		except TypeError:	
			return busServiceEnded

	#Gets Bus Stop ID and Service number that is in request
	def getBusStopID(self):
		return self.busInstance.getbusStopID()
	def getServiceNo(self):
		return self.busInstance.getServiceNo()

	def getNextBusLoad(self):
		return self.busInstance.getNextLoad()
	def getSubsequentBusLoad(self):
		return self.busInstance.getSubsequentLoad()
	
	#Gets the Label object
	def getLabels(self):
		self.alllabels=[self.servicenolabel,
				self.nextbustimelabel,
				self.nextbusloadlabel,
				self.subsequentbustimelabel,
				self.subsequentbusloadlabel,
				self.savebuscheckbox]
		return self.alllabels



class PreferredStops(Screen):
	pass


class BusTimingScreen(Screen):
	#TEST VARIABLES
	_busstopid = 46429
	_serviceno = 911
	
	def getNextBusTime(self):
		Clock.schedule_once(self.updateNextBusTime,_updateFrequency)
		try:
			self.busInstance = datamall.BusInfo(self._busstopid,self._serviceno)
			self.busInstance.scrapeBusInfo()
			dateTime = self.busInstance.getNextTiming()
			grabTime = re.findall('[0-9]+\D[0-9]+\D[0-9]+',dateTime)
			#grabTime[0]==date #grabTime[1]==time(UTC)
			timedelta = datetime.datetime.strptime(grabTime[1],"%H:%M:%S") - datetime.datetime.strptime(DateTimeInfo().getUTCTime(),"%H:%M:%S")
			timeLeft = re.split(r'\D',str(timedelta))
			if dateTime:
				#timeLeft[0] can return null at times
				if not (timeLeft[0]):
					timeLeft[0]=0	
				return '%s MINUTES %s SECONDS' %(str(int(timeLeft[0])*60+int(timeLeft[1])),timeLeft[2])
		except TypeError:
			return busServiceEnded

	def getSubsequentBusTime(self):
		Clock.schedule_once(self.updateSubsequentBusTime,_updateFrequency)
		try:
			self.busInstance = datamall.BusInfo(self._busstopid,self._serviceno)
			self.busInstance.scrapeBusInfo()
			dateTime = self.busInstance.getSubsequentTiming()
			grabTime = re.findall('[0-9]+\D[0-9]+\D[0-9]+',dateTime)
			#grabTime[0]==date #grabTime[1]==time(UTC)
			timedelta = datetime.datetime.strptime(grabTime[1],"%H:%M:%S") - datetime.datetime.strptime(DateTimeInfo().getUTCTime(),"%H:%M:%S")
			timeLeft = re.split(r'\D',str(timedelta))
			if dateTime:
				#timeLeft[0] can return null at times
				if not (timeLeft[0]):
					timeLeft[0]=0	
				return '%s MINUTES %s SECONDS' %(str(int(timeLeft[0])*60+int(timeLeft[1])),timeLeft[2])
		except TypeError:	
			return busServiceEnded


	def updateNextBusTime(self, *args):
		self.ids["nextBusTime"].text = self.getNextBusTime()
	def updateSubsequentBusTime(self, *args):
		self.ids["subsequentBusTime"].text = self.getSubsequentBusTime()


	def getDateTimeNowLabel(self):
		Clock.schedule_once(self.updateDateTimeLabel,1)
		return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	def updateDateTimeLabel(self, *args):
		self.ids["dateTimeNowLabel"].text = self.getDateTimeNowLabel()

	def getBusStopID(self):
		return self.busInstance.getbusStopID()
	def getServiceNo(self):
		return self.busInstance.getServiceNo()


class AskUser(RelativeLayout):
    ''' Callback(bool) if user wants to do something'''
    action_name = StringProperty()
    cancel_name = StringProperty()
    text = StringProperty()
    
    def __init__(self, 
                 action_name='Okay', 
                 cancel_name='Cancel', 
                 text='Are you Sure?',
                 callback=None, # Why would you do this?
                 *args, **kwargs):
        self.action_name = action_name
        self.cancel_name = cancel_name
        self._callback = callback
        self.text = text
        modal_ctl.modal = self
        super(AskUser, self).__init__(*args, **kwargs)

    def answer(self, yesno):
        ''' Callbacks in prompts that open prompts lead to errant clicks'''
        modal_ctl.modal.dismiss()
        if self._callback:
            def delay_me(*args):
                self._callback(yesno)
            Clock.schedule_once(delay_me, 0.1)

class FacebookUI(Screen):
    ''' Seems like there was a bug in the kv that wouldn't bind on 
    app.facebook.status, but only on post_status '''

    status_text = StringProperty()
    def __init__(self, **kwargs):
        super(FacebookUI, self).__init__(**kwargs)
        app.bind(facebook=self.hook_fb)
        self.status_text = 'Facebook Status: [b]{}[/b]\nMessage: [b]{}[/b]'.format('Not Connected','-')
        
    
    def hook_fb(self, app, fb):
        fb.bind(status=self.on_status)
        app.bind(post_status=self.on_status)
        
        #If login is done correctly, self.status will take upon this message
    def on_status(self, instance, status):
        self.status_text = \
        'Facebook Status: [b]{}[/b]\nMessage: [b]{}[/b]'.format(
            app.facebook.status, 
            app.post_status)


class ModalCtl:
    ''' just a container for keeping track of modals and implementing
    user prompts.'''

    def ask_connect(self, tried_connect_callback):
        Logger.info('Opening net connect prompt')
        text = ('You need internet access to do that.  Do you '
                'want to go to settings to try connecting?')
        content = AskUser(text=text,
                          action_name='Settings',
                          callback=tried_connect_callback,	
                          auto_dismiss=False)

        #The Popup widget is used to create modal popups. By default, the popup will cover the whole parent window. When you are creating a popup, you must at least set a Popup.title and Popup.content.
        p = Popup(title = 'Network Unavailable',
                  content = content,
                  size_hint=(0.8, 0.4),
                  pos_hint={'x':0.1, 'y': 0.35})
        modal_ctl.modal = p
        #open popup p
        p.open()

    def ask_retry_facebook(self, retry_purchase_callback):
        Logger.info('Facebook Failed')
        text = ('Zuckerberg is on vacation in Monaco.  Would'
                ' you like to retry?')
        content = AskUser(text=text,
                          action_name='Retry',
                          callback=retry_purchase_callback,
                          auto_dismiss=False)

         #The Popup widget is used to create modal popups. By default, the popup will cover the whole parent window. When you are creating a popup, you must at least set a Popup.title and Popup.content.
        p = Popup(title = 'Facebook Error',
                  content = content,
                  size_hint=(0.8, 0.4),
                  pos_hint={'x':0.1, 'y': 0.35})
        modal_ctl.modal = p
        p.open() 


class ScreenManagement(ScreenManager):
	pass



class ScreenManager(App):
	#Callback properties
	post_status = StringProperty('-')
	user_infos = StringProperty('-')
	facebook = ObjectProperty()
	
	#Class variables
	_facebookid = ''
	_username = ''
	_firstname = ''
	_lastname = ''
	all_saved_busstopNo = []
	all_saved_busno = []

	def build(self):
		global app
		app = self
		#Creating presentation retains an instance that we can reference to
		presentation = Builder.load_file("screenmanager12.kv")
		return presentation
	
	def on_start(self):

		self.facebook = Facebook(FACEBOOK_APP_ID,permissions=['publish_actions', 'basic_info'])
		#Sets up the AskUser() and PopUp() to ask for connection
		global modal_ctl
		modal_ctl = ModalCtl()
		#Define callback as modal_ctl.ask_connect()
		netcheck.set_prompt(modal_ctl.ask_connect)
		self.facebook.set_retry_prompt(modal_ctl.ask_retry_facebook)
		
	#Allows for this app to be paused when Facebook app is opened
	def on_pause(self):
		Logger.info('Android: App paused, now wait for resume.')
		return True
	
	#Allows for this app to be resumed after Facebook authorisation is completed
	def on_resume(self):
		pass

	def fb_me(self):
		def callback(success, user=None, response=None, *args):
			if not success:
			    return
			'''since we're using the JNIus proxy's API here,
			we have to test if we're on Android to avoid implementing
			a mock user class with the verbose Java user interface'''
			if platform() == 'android' and response.getError():
				Logger.info(response.getError().getErrorMessage())
			    #If this platform is android & response type not error
			if platform() == 'android' and not response.getError():
				infos = []
				infos.append('Name: {}'.format(user.getName()))
				infos.append('FirstName: {}'.format(user.getFirstName()))
				infos.append('MiddleName: {}'.format(user.getMiddleName()))
				infos.append('LastName: {}'.format(user.getLastName()))
				infos.append('Link: {}'.format(user.getLink()))
				infos.append('Username: {}'.format(user.getUsername()))
				infos.append('Birthday: {}'.format(user.getBirthday()))
				location = user.getLocation()
				if location:
					infos.append('Country: {}'.format(location.getCountry()))
					infos.append('City: {}'.format(location.getCity()))
					infos.append('State: {}'.format(location.getState()))
					infos.append('Zip: {}'.format(location.getZip()))
					infos.append('Latitude: {}'.format(location.getLatitude()))
					infos.append('Longitude: {}'.format(location.getLongitude()))
				else:
					infos.append('No location available')
				#Get User Details for DB Storage
				#Do something to get the ID part of the Facebook Link. Returns the numerical part of the Link
				self._facebookid = re.findall(r'[0-9]+',user.getLink())[0]
				self._username = user.getUsername()
				self._firstname = user.getFirstName()
				self._lastname = user.getLastName()
				self.startnewSaveThread()
			#if this platform is not android
			else:
				infos = ['ha', 'ha', 'wish', 'this', 'was', 'real']
			self.user_infos = '\n'.join(infos)
		self.facebook.me(callback)

	#separate thread to save basic user information
	def startnewSaveThread(self):
		thread = Thread(target=self.savefacebookinfo,args=())
		thread.start()

	#callback for saving user information
	def savefacebookinfo(self):
		#Use Identifier of the record to retrieve response code from 'users' table
		response = datadb.GetDBInfo().requestRecordByIdentifier("users",self._facebookid)
		Logger.info('Finding user from DreamFactory RESTful API. Response Code: {}'.format(response))
		#If record does not exist, create new FacebookID
		if response.status_code != 200:
			response = datadb.PostDBInfo().createUserTableRecords(self._facebookid,self._firstname+self._lastname,self._firstname,self._lastname)
			Logger.info('Creating user from DreamFactory RESTful API. Response: {}'.format(response))
	
	def getFacebookID(self):
		return self._facebookid

	#non-nus buses = requires bus stop and bus information
	def savePreferredBus(self):
		pass

	def savePreferredNUSBusstop(self):
		pass

	def _toast(self, text, length_long=False):
		toast.toast(text, length_long)

	#GET Request. Returns list of saved busNo and list of saved busstopNo using app._facebookid
	def getUserSaveBusRecords(self):
		#Retrieves for the first time
		if app._facebookid and not (self.all_saved_busstopNo and self.all_saved_busno):
			#gets a list of all the saved buses using facebookid		
			response = datadb.GetDBInfo().requestSavedBusRecord(app._facebookid)
			for each_bus_saved in response['record']:
				self.all_saved_busstopNo.append(each_bus_saved['busstopNo'])
				self.all_saved_busno.append(each_bus_saved['busno'])

if __name__=="__main__":
	ScreenManager().run()
