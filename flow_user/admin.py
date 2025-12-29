from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import CustomUser, Department
from django.contrib.auth.models import Group  # Guruhlarni import qilish

# 1. Import mantiqi
class CustomUserResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'first_name', 'last_name', 'father_name', 'position', 'department')
        import_id_fields = ('username',)
        skip_unchanged = True

    def before_import_row(self, row, **kwargs):
        from django.contrib.auth.hashers import make_password
        
        # 1. Parolni shifrlash
        if 'password' in row and row['password']:
            row['password'] = make_password(str(row['password']))
        
        # 2. Bo'limni avtomat yaratish
        dept_name = row.get('department')
        if dept_name:
            Department.objects.get_or_create(name=dept_name)

    def after_save_instance(self, instance, using_data, dry_run, **kwargs): # <--- **kwargs qo'shildi
        """Foydalanuvchi bazaga saqlangandan so'ng ishlaydi"""
        if not dry_run:
            try:
                # 'user' nomli guruhni qidiramiz yoki yaratamiz
                group, created = Group.objects.get_or_create(name='user')
                # Foydalanuvchiga guruhni qo'shamiz
                instance.groups.add(group)
            except Exception as e:
                print(f"Guruh biriktirishda xato: {e}")

# 2. Admin panelda sozlash
@admin.register(CustomUser)
class CustomUserAdmin(ImportExportModelAdmin, UserAdmin):
    resource_class = CustomUserResource
    list_display = ('username', 'first_name', 'last_name', 'position', 'department')
    
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('position', 'father_name', 'department', 'profile_image')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('position', 'father_name', 'department', 'profile_image')}),
    )