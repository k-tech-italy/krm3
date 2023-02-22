from django.db import models


class ExampleModel1(models.Model):
    example_field_1 = models.CharField(max_length=50)

    def __str__(self):
        return str(self.example_field_1)
