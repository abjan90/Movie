from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import random
import string

# UPDATED IMPORT - Add CancellationRequest
from .models import Movie, Cinema, Screen, Showtime, Seat, Booking, SeatBooking, Payment, CancellationRequest
from .forms import SignUpForm, LoginForm

def generate_booking_reference():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_transaction_id():
    return 'TXN' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

def home(request):
    now_showing = Movie.objects.filter(is_now_showing=True)[:6]
    coming_soon = Movie.objects.filter(is_now_showing=False, release_date__gt=timezone.now())[:6]
    
    context = {
        'now_showing': now_showing,
        'coming_soon': coming_soon,
    }
    return render(request, 'booking/home.html', context)

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = SignUpForm()
    
    return render(request, 'booking/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
                
                if user is not None:
                    login(request, user)
                    messages.success(request, 'Logged in successfully!')
                    next_url = request.GET.get('next', 'home')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Invalid password!')
            except User.DoesNotExist:
                messages.error(request, 'Email not found!')
    else:
        form = LoginForm()
    
    return render(request, 'booking/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')

def movies_list(request):
    movies = Movie.objects.filter(is_now_showing=True)
    
    # Filter by genre
    genre = request.GET.get('genre')
    if genre:
        movies = movies.filter(genre__icontains=genre)
    
    # Filter by language
    language = request.GET.get('language')
    if language:
        movies = movies.filter(language=language)
    
    # Search
    search = request.GET.get('search')
    if search:
        movies = movies.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    context = {
        'movies': movies,
        'genres': Movie.objects.values_list('genre', flat=True).distinct(),
        'languages': Movie.objects.values_list('language', flat=True).distinct(),
    }
    return render(request, 'booking/movies.html', context)

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    
    # Get available showtimes
    selected_date = request.GET.get('date', timezone.now().date())
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    
    selected_cinema = request.GET.get('cinema')
    
    showtimes = Showtime.objects.filter(
        movie=movie,
        start_time__date=selected_date
    ).select_related('screen__cinema')
    
    if selected_cinema:
        showtimes = showtimes.filter(screen__cinema_id=selected_cinema)
    
    # Get all cinemas showing this movie
    cinemas = Cinema.objects.filter(
        screens__showtimes__movie=movie
    ).distinct()
    
    # Generate next 7 days for date selection
    dates = [(timezone.now().date() + timedelta(days=i)) for i in range(7)]
    
    context = {
        'movie': movie,
        'showtimes': showtimes,
        'cinemas': cinemas,
        'dates': dates,
        'selected_date': selected_date,
        'selected_cinema': selected_cinema,
    }
    return render(request, 'booking/movie_detail.html', context)

@login_required
def select_seats(request, showtime_id):
    showtime = get_object_or_404(Showtime, id=showtime_id)
    screen = showtime.screen
    seats = screen.seats.all()
    
    # Get already booked seats for this showtime
    booked_seats = SeatBooking.objects.filter(
        showtime=showtime,
        is_booked=True
    ).values_list('seat_id', flat=True)
    
    if request.method == 'POST':
        selected_seat_ids = request.POST.getlist('seats')
        
        if not selected_seat_ids:
            messages.error(request, 'Please select at least one seat!')
            return redirect('select_seats', showtime_id=showtime_id)
        
        # Create booking with Pending status
        total_amount = len(selected_seat_ids) * float(showtime.price)
        booking = Booking.objects.create(
            user=request.user,
            showtime=showtime,
            total_amount=total_amount,
            status='Pending',  # Changed to Pending
            booking_reference=generate_booking_reference()
        )
        
        # Add seats to booking
        selected_seats = Seat.objects.filter(id__in=selected_seat_ids)
        booking.seats.set(selected_seats)
        
        # Temporarily reserve seats
        for seat_id in selected_seat_ids:
            SeatBooking.objects.update_or_create(
                showtime=showtime,
                seat_id=seat_id,
                defaults={'is_booked': True, 'booking': booking}
            )
        
        # Redirect to payment page
        return redirect('payment_page', booking_id=booking.id)
    
    context = {
        'showtime': showtime,
        'seats': seats,
        'booked_seats': list(booked_seats),
        'screen': screen,
    }
    return render(request, 'booking/select_seats.html', context)

@login_required
def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking is already confirmed
    if booking.status == 'Confirmed':
        return redirect('booking_confirmation', booking_id=booking.id)
    
    context = {
        'booking': booking,
    }
    return render(request, 'booking/payment.html', context)

@login_required
def process_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        # Validate payment method
        if payment_method not in ['card', 'esewa', 'khalti', 'fonepay']:
            messages.error(request, 'Invalid payment method!')
            return redirect('payment_page', booking_id=booking.id)
        
        # Process payment based on method
        if payment_method == 'card':
            card_number = request.POST.get('card_number')
            cardholder_name = request.POST.get('cardholder_name')
            expiry = request.POST.get('expiry')
            cvv = request.POST.get('cvv')
            
            # Basic validation
            if not all([card_number, cardholder_name, expiry, cvv]):
                messages.error(request, 'Please fill in all card details!')
                return redirect('payment_page', booking_id=booking.id)
            
            # Create payment record
            payment = Payment.objects.create(
                booking=booking,
                payment_method=payment_method,
                amount=booking.total_amount,
                transaction_id=generate_transaction_id(),
                status='completed',
                card_number=card_number[-4:],
                cardholder_name=cardholder_name
            )
        else:
            # For digital wallets
            payment = Payment.objects.create(
                booking=booking,
                payment_method=payment_method,
                amount=booking.total_amount,
                transaction_id=generate_transaction_id(),
                status='completed'
            )
        
        # Update booking status to Confirmed
        booking.status = 'Confirmed'
        booking.save()
        
        messages.success(request, 'Payment successful! Your booking is confirmed.')
        return redirect('booking_confirmation', booking_id=booking.id)
    
    return redirect('payment_page', booking_id=booking.id)

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Get payment details if exists
    payment = None
    try:
        payment = booking.payment
    except Payment.DoesNotExist:
        pass
    
    context = {
        'booking': booking,
        'payment': payment,
    }
    return render(request, 'booking/booking_confirmation.html', context)

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    
    context = {
        'bookings': bookings,
    }
    return render(request, 'booking/my_bookings.html', context)

# ============================================
# NEW CANCELLATION VIEWS
# ============================================

@login_required
def request_cancellation(request, booking_id):
    """Display the cancellation request form"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if can request cancellation
    if not booking.can_request_cancellation():
        messages.error(request, 'This booking cannot be cancelled or already has a pending cancellation request.')
        return redirect('my_bookings')
    
    context = {
        'booking': booking,
    }
    return render(request, 'booking/request_cancellation.html', context)

@login_required
def cancel_booking(request, booking_id):
    """Process the cancellation request"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, 'Please provide a reason for cancellation.')
            return redirect('request_cancellation', booking_id=booking.id)
        
        if len(reason) < 10:
            messages.error(request, 'Reason must be at least 10 characters long.')
            return redirect('request_cancellation', booking_id=booking.id)
        
        # Check if can request cancellation
        if not booking.can_request_cancellation():
            messages.error(request, 'This booking cannot be cancelled.')
            return redirect('my_bookings')
        
        # Create cancellation request
        CancellationRequest.objects.create(
            booking=booking,
            reason=reason
        )
        
        messages.success(request, 'Cancellation request submitted successfully! Our admin will review it shortly.')
        return redirect('my_bookings')
    
    return redirect('request_cancellation', booking_id=booking.id)
