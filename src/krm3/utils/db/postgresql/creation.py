# import sys
#
# from django.db.backends.postgresql import creation as original_creation
#
#
# class DatabaseCreation(original_creation.DatabaseCreation):
#
#     def _execute_create_test_db(self, cursor, parameters, keepdb=False):
#         try:
#             if keepdb and self._database_exists(cursor, parameters['dbname']):
#                 # If the database should be kept and it already exists, don't
#                 # try to create a new one.
#                 return
#             super()._execute_create_test_db(cursor, parameters, keepdb)
#             cursor.execute('CREATE SCHEMA IF NOT EXISTS django')
#         except Exception as e:
#             if getattr(e.__cause__, 'pgcode', '') != errorcodes.DUPLICATE_DATABASE:
#                 # All errors except "database already exists" cancel tests.
#                 self.log('Got an error creating the test database: %s' % e)
#                 sys.exit(2)
#             elif not keepdb:
#                 # If the database should be kept, ignore "database already
#                 # exists".
#                 raise
