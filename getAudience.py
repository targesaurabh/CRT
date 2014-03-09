import os, sys
from flask import render_template, request, Response, Flask, json, Blueprint
from facepy import GraphAPI
from pymongo import Connection
import datetime
import csv
import time
import threading
from celery import result
from fetchData import fLike, fComment, fPost, dummytask

audienceapp= Blueprint('audienceapp', __name__,template_folder='templates',static_folder='static')

class CommonData(threading.Thread):	
		con = Connection('localhost')
		db = con['fbdata']

		def __init__(self, page_name):
			threading.Thread.__init__(self)	
			self.allTasksSet = ''
			self.nextUrl = ''
			self.graphObj = ''
			self.postFlag = True  #if true fetch next posts else stop fetching
			self.pageName = page_name

		#generate csv file for all userid of given page
		def csvFile(self, pageId, pageName):							
			allIds = CommonData.db.allUserId.find({"pageId":pageId})	
			path = os.path.join('static', 'csvFiles', pageName+'.csv')	
			print path
			with open(path, 'wb') as csvfile:
			    spamwriter = csv.writer(csvfile, delimiter=' ',quotechar='|', quoting=csv.QUOTE_MINIMAL)
			    for i in allIds:	    	
				    spamwriter.writerow([i['fbId']])
			return True			
		
		#fetch data of given facebook pageid			        
		def fetchPost(self, pageId):		
			#get all posts		
			postsData = self.graphObj.get(self.nextUrl)  
			if(postsData['data']):
				#form new url to get next 25 posts
				self.nextUrl = postsData['paging']['next'].strip('https://graph.facebook.com')	
				print 'posts fetched and ready to traverse'				
				for p in postsData['data']:
					postID = p['id']						
					#start worker for getting likes on given post			
					rL = fLike.delay(self.graphObj, postID, pageId)
					#start worker for getting comments on given post			
					rC = fComment.delay(self.graphObj, postID, pageId)
					#create resultset and add like and comment workers' result object to check their status later on
					self.allTasksSet = result.ResultSet([])					
					self.allTasksSet.add(rL)
					self.allTasksSet.add(rC)	
			else:			
				self.postFlag = False
				print 'Posts Empty'		

		def checkResultCompletion(self, pageId):						
			#total userids stored in database of any pageid
			idCount = CommonData.db.allUserId.find({"pageId":pageId}).count()				
			if(self.allTasksSet.ready()):
				#if all tasks are finished then clear resultset
				self.allTasksSet.clear()
				#if id count not yet 5000 and posts are not yet empty then fetch next posts
				if(self.postFlag and idCount < 5000):					
					self.fetchPost(pageId)					
				else:
					#create csv file for given page if no posts remaining or required id count achieved
					print self.pageName									
					self.csvFile(pageId, self.pageName)
					return True
			return False				

		#after 3 seconds check whether all tasks are finished or not	
		def startTimer(self, pageId):			
			if(not self.checkResultCompletion(pageId)):				
				print 'conditions not satisfied yet for '+pageId
				# time.sleep(5)
				t = threading.Timer(3, self.startTimer, args=[pageId])
				t.start()		
				# self.startTimer(pageId)				    	    			

		def run(self):
			print 'Activity started'						

#gets page name here after user submit it
@audienceapp.route('/getPosts', methods = ['Post'])
def getPosts():	
	comObj = CommonData(request.form['pageName'])
	comObj.start()	#start thread of CRT
	print request.form['pid']		
	pageId = request.form['pid']
	access_token = request.form['access_token']	
	comObj.graphObj = GraphAPI(access_token)		
	#form url to get facebook posts
	comObj.nextUrl = pageId+'/posts' 
	comObj.fetchPost(pageId)
	comObj.startTimer(pageId)	
	resp = Response('done', status=200, mimetype='text/plain')
	return resp

#get facebook page name
@audienceapp.route('/audience')
def getData():	
	return render_template('getPageId.html');	
	
# @audienceapp.route('/csvFile', methods = ['Post'])
# def csvFile():	
# 	pageId = request.form['pageId']
# 	pageName = request.form['pageName']
# 	allIds = CommonData.db.allUserId.find({"pageId":pageId})	
# 	path = os.path.join('static', 'csvFiles', pageName+'.csv')	
# 	print path
# 	with open(path, 'wb') as csvfile:
# 	    spamwriter = csv.writer(csvfile, delimiter=' ',quotechar='|', quoting=csv.QUOTE_MINIMAL)
# 	    for i in allIds:	    	
# 		    spamwriter.writerow([i['fbId']])	    
# 	return 'done'    


		
@audienceapp.route('/checkStatus', methods = ['Post'])
def checkStatus():
	pageId = request.form['pageId']
	pCount = int(request.form['previousCount'])
	print 'pCount : '
	print pCount	
	idCount = CommonData.db.allUserId.find({"pageId":pageId}).count()	
	print 'idCount : '
	print idCount
	if((idCount<5000) or (pCount<idCount)):
		if((pCount==idCount) and (pCount!=0)):
			resp = Response(str('True'), status=200, mimetype='text/plain')
			return resp
		else:
			resp = Response(str(idCount), status=200, mimetype='text/plain')
			return resp	
	else:		
		resp = Response(str('True'), status=200, mimetype='text/plain')
		return resp
		

