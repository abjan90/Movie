from django.contrib import admin
from .models import Cinema, Movie, Screen, Showtime, Seat, Booking, SeatBooking

@admin.register(Cinema)
class CinemaAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'phone']
    search_fields = ['name', 'location']

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'genre', 'language', 'rating', 'release_date', 'is_now_showing']
    list_filter = ['is_now_showing', 'rating', 'genre', 'language']
    search_fields = ['title', 'description']

@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['name', 'cinema', 'total_seats']
    list_filter = ['cinema']

@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = ['movie', 'screen', 'start_time', 'price']
    list_filter = ['movie', 'screen__cinema', 'start_time']
    date_hierarchy = 'start_time'

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['screen', 'row', 'number', 'seat_type']
    list_filter = ['screen', 'seat_type']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'user', 'showtime', 'total_amount', 'status', 'booking_date']
    list_filter = ['status', 'booking_date']
    search_fields = ['booking_reference', 'user__username']

@admin.register(SeatBooking)
class SeatBookingAdmin(admin.ModelAdmin):
    list_display = ['showtime', 'seat', 'is_booked']
    list_filter = ['is_booked', 'showtime']
