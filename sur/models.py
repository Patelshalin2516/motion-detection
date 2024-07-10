from django.db import models

class MotionAlert(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    image = models.BinaryField(default=b'')
    distance = models.FloatField()

    def __str__(self):
        return f"Alert at {self.timestamp} - Distance: {self.distance:.2f}m"
