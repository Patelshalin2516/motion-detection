from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('sur.urls')),
    path('', include('otp_app.urls'))
]
