from django.db import models

from krm3.models import City, Project, Resource


class Mission(models.Model):
    from_date = models.DateField()
    to_date = models.DateField()

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.id} {self.from_date} -- {self.to_date}'
