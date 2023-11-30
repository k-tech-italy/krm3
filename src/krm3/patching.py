# def patch_adminfilters():
#     from adminfilters.numbers import NumberFilter
#     from django.contrib.admin.options import IncorrectLookupParameters
#
#     def queryset(self, request, queryset):
#         if self.value() and self.value()[0]:
#             raw_value = self.value()[0]
#             m1 = self.rex1.match(raw_value)
#             m_range = self.re_range.match(raw_value)
#             m_list = self.re_list.match(raw_value)
#             m_unlike = self.re_unlike.match(raw_value)
#             if m_unlike and m_unlike.groups():
#                 match = '%s__exact' % self.field_path
#                 op, value = self.re_unlike.match(raw_value).groups()
#                 queryset = queryset.exclude(**{match: value})
#             else:
#                 if m1 and m1.groups():
#                     op, value = self.rex1.match(raw_value).groups()
#                     match = '%s__%s' % (self.field_path, self.map[op or '='])
#                     self.filters = {match: value}
#                 elif m_range and m_range.groups():
#                     start, end = self.re_range.match(raw_value).groups()
#                     self.filters = {
#                         f'{self.field_path}__gte': start,
#                         f'{self.field_path}__lte': end,
#                     }
#                 elif m_list and m_list.groups():
#                     value = raw_value.split(',')
#                     match = '%s__in' % self.field_path
#                     self.filters = {match: value}
#                 # elif m_unlike and m_unlike.groups():
#                 #     match = '%s__exact' % self.field.name
#                 #     op, value = self.re_unlike.match(raw).groups()
#                 #     queryset = queryset.exclude(**{match: value})
#                 else:  # pragma: no cover
#                     raise IncorrectLookupParameters()
#                 try:
#                     queryset = queryset.filter(**self.filters)
#                 except Exception:
#                     raise IncorrectLookupParameters(self.value())
#         return queryset
#
#     NumberFilter.queryset = queryset
#
#
# patch_adminfilters()
