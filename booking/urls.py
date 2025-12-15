from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('movies/', views.movies_list, name='movies'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('showtime/<int:showtime_id>/seats/', views.select_seats, name='select_seats'),
    path('booking/<int:booking_id>/confirmation/', views.booking_confirmation, name='booking_confirmation'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
]