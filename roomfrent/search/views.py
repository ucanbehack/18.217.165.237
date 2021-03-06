from django.shortcuts import render

# Create your views here.
import base64
import csv
from datetime import datetime
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
import json,pprint
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login,logout
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from . import models
from search.models import *
from passlib.hash import django_pbkdf2_sha256 as handler
import pytz
from random import randint
import requests
from django.db import connection
from django.core import serializers
import json,random,string

# google map api
import googlemaps
from datetime import datetime
gmaps = googlemaps.Client(key='AIzaSyC95eHImBVWI4SbTc3DD2zruYGcWdI6xD0')

# from login.models import *
utc = pytz.UTC


    # ADMIN



class HomePage(TemplateView):
    template_name = "dashboard.html"


    def get_context_data(self, * args, ** kwargs):
        context = super(HomePage, self).get_context_data()
        self.request.environ['REMOTE_ADDR']
        # context['user']=self.request.user
        if self.request.user.is_anonymous:
            context['user'] = "Guest"
        else:
            context['user'] = self.request.user.first_name
      
        return context

    def validate_username(request):
        username = request.GET.get('mobile', None)
        data = {
        'is_taken': User.objects.filter(username__iexact=username).exists()
        }
        return JsonResponse(data)
    @csrf_exempt
    def owner_register(request):
        password = request.POST.get('password')
        mobile = request.POST.get('mobile')
        email = request.POST.get('email')
        first_name = request.POST.get('name')
        if request.is_ajax():
            user=User.objects.create_user(mobile, email, password)
            user.first_name = first_name
            user.is_active = False
            user.save()
            confirmation_code = ''.join(random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for x in range(33))
            owner_register = OwnerInfo(user=user)
            owner_register.owner_mobile=mobile
            owner_register.confirmation_code = confirmation_code
            owner_register.save()
            # user = authenticate(username=mobile, password=password)
            p=OwnerInfo.objects.get(user=user)
            current_site = get_current_site(request)
            content = current_site.domain+"/owner/activate" +  user.username + "/" + str(p.confirmation_code) 
            send_mail("Email Verify", content, 'no-reply@gsick.com', [user.email], fail_silently=False)
            data = {'sucess':True,'status':1,'message':'Please confirm your email address to complete the registration'}

            return JsonResponse(data)

    def user_login(request):
        if request.method == "POST":
            password = request.POST.get('password')
            mobile = request.POST.get('mobile')
            user = authenticate(username=mobile, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    data = {'sucess':True,'status':2}
                    return JsonResponse(data)
                    # return HttpResponseRedirect("/owner/?own=" + str(user.id))
                else:
                    data = {'sucess':True,'status':1,'message':'Please confirm your email address to complete the registration'}
                    return JsonResponse(data)
            else:
                data = {'sucess':True,'status':0,'message':'Invalid password. Please try again'}
                return JsonResponse(data)
    

class SearchResults(TemplateView):
    template_name = "search_results.html"
    def get_context_data(self, * args, ** kwargs):
        context = super(SearchResults, self).get_context_data()
        # database_result = Property.objects.filter(location=search_result)
        # g = googlemap(search_result)
        # print nearby_place
        context['lat'] = self.request.GET.get('lat')
        context['lng'] = self.request.GET.get('lng')
        context['search_result'] = self.request.GET.get('search')

        if self.request.user.is_anonymous:
            context['user'] = "Guest"
        else:
            context['user'] = self.request.user.first_name
        return context
    def post(self, request):
        # print request.POST
        search_result = request.POST.get('search_query')
        getlat= request.POST.get('lat')
        getlng= request.POST.get('lng')
        if getlat:
            lat =getlat
            lng =getlng
        else:
            result_add_query = gmaps.places(search_result)
            lat=result_add_query['results'][0]['geometry']['location']['lat']
            lng=result_add_query['results'][0]['geometry']['location']['lng']
        cursor = connection.cursor()
        query='SELECT id,( 6371 * acos(cos(radians('+str(lat)+'))* cos(radians(lat)) * cos(radians(lng) - radians('+str(lng)+')) + sin(radians('+str(lat)+')) * sin(radians(lat )))) AS distance_KM ,location,name FROM search_property HAVING distance_KM >= 0 ORDER BY distance_KM '
        # print query
        # cursor.execute('''SELECT id,( 6371 * acos(cos(radians(lat)) * cos(radians(lat)) * cos(radians(lng) - radians(77.5612252)) + sin(radians(28.4581258)) * sin(radians(lat )))) AS distance_KM FROM search_property HAVING distance_KM > 50 ORDER BY distance_KM LIMIT 0, 20;''')
        # result_set = dictfetchall(cursor)
        all_results=[]
        all_property=Property.objects.raw(query)
        image_url=[]
        json={}

        for i in all_property:
            json={}
            images_query='SELECT id,url from search_images WHERE property_id_id=' + str(i.id)
            images =Images.objects.raw(images_query)
            json['id']=str(i.id)
            json['name']=str(i.name)
            json['distance']=str(i.distance_KM)
            json['budget']=str(i.budget)
            json['created_at']=str(i.created_at)
            json['location']=str(i.location)
            json['owner']=str(i.owner.user.first_name)
            json['owner_id']=str(i.owner.user.id)
            json['owner_mob']=str(i.owner.owner_mobile)
            json['furnish']=str(i.furnish_id)
            json['preference']=str(i.preference.girls) + "," + str(i.preference.family) + "," +str(i.preference.bachelor)

            for x in images:
                image_url=str(x.url)
                json['image']=image_url
            # json['image']=list(Images.objects.filter(property_id=i.id))

            all_results.append(json)
        return JsonResponse(all_results, safe=False)
    def get_contact(request):
        owner_id = request.POST.get('owner_id')
        user_details=OwnerInfo.objects.get(user_id=owner_id)
        user_name=User.objects.get(id=owner_id)
        return JsonResponse({'mobile':user_details.owner_mobile,'owner_name':user_name.first_name})
