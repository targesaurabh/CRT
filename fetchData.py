from __future__ import absolute_import
from pymongo import Connection
from facepy import GraphAPI

from celerytasks import celery

con = Connection('localhost')
db = con['fbdata']


@celery.task
def dummytask():
	db.stubdata.insert({'b':'12'})


@celery.task
def fPost(graph, pageId):
	postsData = graph.get(pageId+'/posts')  	
	for p in postsData['data']:
		postID = p['id']				
		rL = fLike.delay(graph, postID, pageId)
		rC = fComment.delay(graph, postID, pageId)				
	

#get data of comments of any postid
#page id to be used as a key to store userIds
@celery.task
def fComment(graph, postID, pageId):
	commentsData = graph.get(postID + '/comments')
	while(commentsData['data']):
		print len(commentsData['data'])
		for c in commentsData['data']:				
			db.allUserId.insert({"fbId" : str(c['from']['id']), "pageId" : pageId})	
		#facebook gives 25 comments of any post and gives next url to get next 25
		if(len(commentsData['data']) == 25):					
			after = commentsData['paging']['cursors']['after']
			commentsData = graph.get(postID + '/comments?after='+after)
		else:
			break	

#get data of likes of any postid
#page id to be used as a key to store userIds
@celery.task
def fLike(graph, postID, pageId):
	likesData = graph.get(postID + '/likes')
	while(likesData['data']):
		print len(likesData['data'])
		for l in likesData['data']:				
			db.allUserId.insert({"fbId" : str(l['id']), "pageId" : pageId})										
		#facebook gives 25 likes of any post and gives next url to get next 25		
		if(len(likesData['data']) == 25):
			after = likesData['paging']['cursors']['after']						
			likesData = graph.get(postID + '/likes?after='+after)
		else:
			break	
