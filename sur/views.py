import requests

from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse
from .models import MotionAlert
from .forms import SignupForm
from django.contrib.auth import login
import cv2
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64

# Constants for distance calculation
KNOWN_WIDTH = 0.2  # Known width of the object in meters (example: 20 cm)
FOCAL_LENGTH = 615  # Focal length of the camera (adjust based on your camera)
TELEGRAM_BOT_TOKEN = 'token_id'  # Replace with your Telegram bot token
TELEGRAM_CHAT_ID = 'chat_id'  # Replace with your Telegram chat ID

def detect_motion(frame1, frame2):
    # Convert frames to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to the frames
    gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
    
    # Compute the absolute difference between the two frames
    frame_delta = cv2.absdiff(gray1, gray2)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    
    # Find contours on the thresholded image
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Check if any contour area is significant
    motion_detected = any(cv2.contourArea(c) > 500 for c in contours)
    
    return motion_detected, contours

def calculate_distance(known_width, focal_length, perceived_width):
    if perceived_width == 0:
        return None
    return (known_width * focal_length) / perceived_width

def send_telegram_alert(alert_time, image_data, distance):
    try:
        # Create the alert message
        message_text = f"Alert! Unsafe condition occur.\nMotion detected at {alert_time}.\nDistance to object: {distance:.2f} meters."
        
        # Send the message
        send_message_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(send_message_url, data={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message_text
        })

        # Check if the message was sent successfully
        if response.status_code == 200:
            print(f"Alert message sent to Telegram chat ID {TELEGRAM_CHAT_ID}.")
        else:
            print(f"Failed to send alert message: {response.status_code} {response.text}")
        
        # Send the image
        send_photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        response = requests.post(send_photo_url, data={
            'chat_id': TELEGRAM_CHAT_ID
        }, files={
            'photo': ('image.jpg', image_data, 'image/jpeg')
        })

        # Check if the image was sent successfully
        if response.status_code == 200:
            print(f"Alert image sent to Telegram chat ID {TELEGRAM_CHAT_ID}.")
        else:
            print(f"Failed to send alert image: {response.status_code} {response.text}")

    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def motion_detection_view(request):
    return render(request, 'home.html')

def gen(camera):
    time.sleep(2)  # Warm up the camera
    last_frame = None
    alert_issued = False
    alert_interval = 10  # seconds
    last_alert_time = 0
    frame_rate = 30  # frames per second
    prev_time = 0

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        # Resize the frame to reduce data size
        frame = cv2.resize(frame, (640, 480))

        # Get the current time
        current_time = time.time()

        # Skip frames to achieve the desired frame rate
        if current_time - prev_time > 1.0 / frame_rate:
            prev_time = current_time

            if last_frame is None:
                last_frame = frame
                continue

            motion_detected, contours = detect_motion(last_frame, frame)

            if motion_detected and (current_time - last_alert_time > alert_interval):
                alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                image_data = cv2.imencode('.jpg', frame)[1].tostring()
                print(f"Motion detected at {alert_time}! Alert issued.")

                for contour in contours:
                    if cv2.contourArea(contour) > 50000:
                        (x, y, w, h) = cv2.boundingRect(contour)
                        distance = calculate_distance(KNOWN_WIDTH, FOCAL_LENGTH, w)
                        if distance is not None and 0 <= distance <= 3:
                            cv2.line(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.putText(frame, f"Distance: {distance:.2f}m", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            send_telegram_alert(alert_time, image_data, distance)
                            MotionAlert.objects.create(image=image_data, distance=distance)
                            last_alert_time = current_time
                            break  # Only send one alert per detection

            # Update the last frame
            last_frame = frame

            # Convert the frame to JPEG format
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame = jpeg.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def video_feed(request):
    url = 'http://192.168.1.6:8080/video'  # Replace with your URL
    cap = cv2.VideoCapture(url)
    return StreamingHttpResponse(gen(cap), content_type="multipart/x-mixed-replace;boundary=frame")

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log the user in after signup
            return redirect('home')  # Redirect to the home page
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def home(request):
    return render(request, 'home.html')

def index(request):
    return render(request, 'index.html')

def object_detection(request):
    return render(request, 'object_detection.html')

def display_images(request):
    alerts = MotionAlert.objects.all()  # Query all MotionAlert instances
    for alert in alerts:
        alert.image = base64.b64encode(alert.image).decode('utf-8')
    return render(request, 'display_images.html', {'alerts': alerts})

def get_chat_id():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    data = response.json()
    print(data)  # This will print the response data to help you find the chat ID

get_chat_id()
