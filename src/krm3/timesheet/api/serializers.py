from rest_framework import serializers

from krm3.timesheet.models import Task, TimeEntry


class TimeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = (
            'id',
            'date',
            'last_modified',
            'work_hours',
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'overtime_hours',
            'on_call_hours',
            'travel_hours',
            'rest_hours',
            'state',
            'comment',
        )


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class TimesheetTaskSerializer(TaskSerializer):
    project_name = serializers.SerializerMethodField()
    time_entries = TimeEntrySerializer(many=True, read_only=True)

    class Meta(TaskSerializer.Meta):
        fields = (
            'id',
            'title',
            'basket_title',
            'color',
            'start_date',
            'end_date',
            'time_entries',
            'project_name',
        )

    def get_project_name(self, obj: Task) -> str:
        return obj.project.name
