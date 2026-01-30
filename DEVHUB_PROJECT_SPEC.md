# DevHub - Developer Collaboration Platform

## Proje Özeti

GitHub + Slack + Notion karışımı bir platform. Geliştiricilerin projelerini yönettiği, takımlarla işbirliği yaptığı, real-time iletişim kurduğu bir platform.

**Amaç:** Tek bir proje üzerinden Django, DRF ve backend engineering kavramlarını öğrenmek.

**Yaklaşım:** Her modülü sırayla tamamla, acele etme, öğrenmeye odaklan.

---

# MODÜL 1: Proje Kurulumu & Temel Modeller

## Hedef
Django projesi oluştur, temel modelleri tasarla ve implement et.

## Öğreneceklerin
- Django proje yapısı
- Custom User model
- Model relationships (ForeignKey, ManyToMany, OneToOne)
- Model managers
- Database migrations
- Django Admin

## Adımlar

### Adım 1.1: Proje Oluşturma

```bash
# Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Django kurulumu
pip install django djangorestframework

# Proje oluştur
django-admin startproject config .

# Apps oluştur
python manage.py startapp users
python manage.py startapp organizations
python manage.py startapp projects
```

**Proje Yapısı:**
```
devhub/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── users/
├── organizations/
├── projects/
├── manage.py
└── requirements.txt
```

### Adım 1.2: Settings Yapılandırması

**config/settings.py:**
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    
    # Local apps
    'users',
    'organizations',
    'projects',
]

# Custom User Model - ÖNEMLİ: İlk migration'dan önce ayarla!
AUTH_USER_MODEL = 'users.User'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### Adım 1.3: User Modeli

**users/models.py:**
```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model.
    
    Neden AbstractUser?
    - Django'nun default User modelini extend ediyoruz
    - Sonradan field eklemek zor, baştan custom yapmak best practice
    - AbstractUser: username, email, password, first_name, last_name hazır gelir
    """
    
    # Ek alanlar
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.URLField(blank=True)  # Şimdilik URL, sonra S3 ekleyeceğiz
    job_title = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username
```

**Öğrenme Noktaları:**
- `AbstractUser` vs `AbstractBaseUser`: AbstractUser hazır field'larla gelir, AbstractBaseUser sıfırdan başlar
- `auto_now_add`: Sadece oluşturulurken set edilir
- `auto_now`: Her save'de güncellenir
- `db_table`: Tablo adını özelleştir
- `ordering`: Default sıralama

### Adım 1.4: Organization Modeli

**organizations/models.py:**
```python
from django.db import models
from django.conf import settings


class Organization(models.Model):
    """
    Organizasyon modeli.
    
    Bir organizasyonun birden fazla üyesi olabilir.
    Bir kullanıcı birden fazla organizasyona üye olabilir.
    """
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)  # URL-friendly identifier
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo = models.URLField(blank=True)
    
    # Owner - Organizasyonu oluşturan kişi
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # Owner silinirse org silinmesin
        related_name='owned_organizations'
    )
    
    # Members - ManyToMany through ile ara tablo
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='OrganizationMember',
        related_name='organizations'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    """
    Organization-User ara tablosu.
    
    Neden through model?
    - Üyelik bilgisi tutmak için (role, joined_at)
    - ManyToMany'ye ekstra field eklemek için
    """
    
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'
        VIEWER = 'viewer', 'Viewer'
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'organization_members'
        unique_together = ['organization', 'user']  # Bir user bir org'a bir kez üye olabilir
    
    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"
```

**Öğrenme Noktaları:**
- `ForeignKey on_delete` seçenekleri:
  - `CASCADE`: Parent silinince child da silinir
  - `PROTECT`: Parent silinmesini engeller
  - `SET_NULL`: Parent silinince NULL yapar (null=True gerekir)
  - `SET_DEFAULT`: Default değere set eder
- `ManyToManyField through`: Ara tabloya ekstra field eklemek için
- `TextChoices`: Enum benzeri, database'de string saklar
- `unique_together`: Composite unique constraint
- `related_name`: Reverse relation için isim

### Adım 1.5: Project Modeli

**projects/models.py:**
```python
from django.db import models
from django.conf import settings


class Project(models.Model):
    """
    Proje modeli.
    
    Her proje bir organizasyona aittir.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'
        DELETED = 'deleted', 'Deleted'  # Soft delete için
    
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'
    
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    
    # Relations
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='projects'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects'
    )
    
    # Settings
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'projects'
        unique_together = ['organization', 'slug']  # Org içinde unique slug
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.organization.name}/{self.name}"


class Task(models.Model):
    """
    Task modeli.
    
    Her task bir projeye aittir.
    Task'lar birbirine bağlanabilir (parent-child).
    """
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    class Status(models.TextChoices):
        TODO = 'todo', 'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        IN_REVIEW = 'in_review', 'In Review'
        DONE = 'done', 'Done'
        CANCELLED = 'cancelled', 'Cancelled'
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Relations
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )
    
    # Self-referential - Subtasks için
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks'
    )
    
    # Task details
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO
    )
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tasks'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class TaskComment(models.Model):
    """
    Task yorumları.
    """
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='task_comments'
    )
    content = models.TextField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'task_comments'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author} on {self.task}"
```

**Öğrenme Noktaları:**
- Self-referential ForeignKey: `parent = models.ForeignKey('self', ...)` - Subtask için
- `DecimalField`: Para, saat gibi hassas değerler için (FloatField yerine)
- Soft delete pattern: `status = 'deleted'` yerine gerçekten silmemek

### Adım 1.6: Migrations

```bash
# Migration oluştur
python manage.py makemigrations

# Migration'ları kontrol et
python manage.py showmigrations

# Migration'ları uygula
python manage.py migrate
```

**Öğrenme Noktaları:**
- `makemigrations`: Model değişikliklerini migration dosyasına yazar
- `migrate`: Migration'ları database'e uygular
- Migration dosyalarını version control'e ekle
- Production'da migration dikkatli yapılmalı (data loss riski)

### Adım 1.7: Admin Panel

**users/admin.py:**
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    # Ek alanları admin formuna ekle
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('bio', 'avatar', 'job_title')}),
    )
```

**organizations/admin.py:**
```python
from django.contrib import admin
from .models import Organization, OrganizationMember


class OrganizationMemberInline(admin.TabularInline):
    model = OrganizationMember
    extra = 1
    autocomplete_fields = ['user']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner', 'member_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['owner']
    inlines = [OrganizationMemberInline]
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__username', 'organization__name']
    autocomplete_fields = ['user', 'organization']
```

**projects/admin.py:**
```python
from django.contrib import admin
from .models import Project, Task, TaskComment


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ['title', 'status', 'priority', 'assignee', 'due_date']
    autocomplete_fields = ['assignee']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'status', 'visibility', 'task_count', 'created_at']
    list_filter = ['status', 'visibility', 'created_at']
    search_fields = ['name', 'slug', 'organization__name']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['organization', 'created_by']
    inlines = [TaskInline]
    
    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = 'Tasks'


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    fields = ['author', 'content', 'created_at']
    readonly_fields = ['created_at']
    autocomplete_fields = ['author']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'priority', 'assignee', 'due_date']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['title', 'description', 'project__name']
    autocomplete_fields = ['project', 'assignee', 'created_by', 'parent']
    inlines = [TaskCommentInline]
    date_hierarchy = 'created_at'


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'task__title', 'author__username']
    autocomplete_fields = ['task', 'author']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
```

**Öğrenme Noktaları:**
- `@admin.register`: Decorator ile register
- `list_display`: Liste sayfasında gösterilecek alanlar
- `list_filter`: Sağ tarafta filtre
- `search_fields`: Arama alanları
- `prepopulated_fields`: Otomatik doldurma (slug için)
- `autocomplete_fields`: Büyük tablolar için autocomplete
- `Inline`: İlişkili modelleri aynı sayfada düzenle
- Custom method: `member_count` gibi hesaplanmış alanlar

### Adım 1.8: Superuser Oluştur ve Test Et

```bash
# Superuser oluştur
python manage.py createsuperuser

# Server'ı başlat
python manage.py runserver

# Admin panele git: http://localhost:8000/admin/
```

**Test Senaryoları:**
1. User oluştur
2. Organization oluştur, owner olarak user'ı seç
3. Organization'a member ekle
4. Project oluştur
5. Task oluştur, assignee ata
6. Subtask oluştur (parent seç)
7. Comment ekle

---

## Ödevler

### Ödev 1: Model Manager
`Project` modeline custom manager ekle:
- `active()`: Sadece active projeleri getir
- `by_organization(org_id)`: Belirli org'un projelerini getir

```python
class ProjectManager(models.Manager):
    def active(self):
        return self.filter(status=Project.Status.ACTIVE)
    
    def by_organization(self, org_id):
        return self.filter(organization_id=org_id)

class Project(models.Model):
    # ...
    objects = ProjectManager()
```

### Ödev 2: Model Signal
User oluşturulduğunda otomatik olarak "Personal" adında bir organization oluştur:

```python
# users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from organizations.models import Organization, OrganizationMember


@receiver(post_save, sender=User)
def create_personal_organization(sender, instance, created, **kwargs):
    if created:
        org = Organization.objects.create(
            name=f"{instance.username}'s Workspace",
            slug=f"{instance.username}-workspace",
            owner=instance
        )
        OrganizationMember.objects.create(
            organization=org,
            user=instance,
            role=OrganizationMember.Role.OWNER
        )
```

### Ödev 3: Query Optimization
Şu query'yi optimize et (N+1 problemi var):

```python
# Kötü - N+1 query
projects = Project.objects.all()
for project in projects:
    print(project.organization.name)  # Her project için ayrı query
    print(project.created_by.username)  # Her project için ayrı query

# İyi - select_related ile
projects = Project.objects.select_related('organization', 'created_by').all()
```

### Ödev 4: Soft Delete
`Task` modeline soft delete ekle:
- `is_deleted` field ekle
- `delete()` metodunu override et
- Custom manager ile deleted task'ları filtrele

---

## Kontrol Listesi

- [ ] Django projesi oluşturuldu
- [ ] Custom User modeli oluşturuldu
- [ ] Organization modeli oluşturuldu
- [ ] OrganizationMember (through) modeli oluşturuldu
- [ ] Project modeli oluşturuldu
- [ ] Task modeli oluşturuldu
- [ ] TaskComment modeli oluşturuldu
- [ ] Migrations çalıştırıldı
- [ ] Admin panel yapılandırıldı
- [ ] Superuser oluşturuldu
- [ ] Admin panelden test edildi
- [ ] Ödev 1: Model Manager tamamlandı
- [ ] Ödev 2: Model Signal tamamlandı
- [ ] Ödev 3: Query Optimization anlaşıldı
- [ ] Ödev 4: Soft Delete tamamlandı

---

## Sonraki Modül

Modül 1'i tamamladıktan sonra **Modül 2: Serializers & Validation**'a geç.

Modül 2'de:
- DRF Serializers
- Nested serializers
- Custom validation
- SerializerMethodField
- Read/Write serializers

---

## Kaynaklar

- [Django Models Documentation](https://docs.djangoproject.com/en/5.0/topics/db/models/)
- [Django Admin Documentation](https://docs.djangoproject.com/en/5.0/ref/contrib/admin/)
- [Django Signals](https://docs.djangoproject.com/en/5.0/topics/signals/)
- [Django QuerySet API](https://docs.djangoproject.com/en/5.0/ref/models/querysets/)


---

# MODÜL 2: Serializers & Validation

## Hedef
DRF Serializers kullanarak API'ler için veri dönüşümü ve validation yapmak.

## Öğreneceklerin
- ModelSerializer vs Serializer
- Nested serializers
- Custom validation
- SerializerMethodField
- Read/Write serializers
- Partial update

## Adımlar

### Adım 2.1: Temel User Serializer

**users/serializers.py:**
```python
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    User için temel serializer.
    
    ModelSerializer:
    - Model field'larını otomatik serializer field'larına çevirir
    - create() ve update() metodları hazır gelir
    """
    
    # Computed field - database'de yok, hesaplanıyor
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'bio', 'avatar', 'job_title', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_full_name(self, obj):
        """SerializerMethodField için getter metodu."""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class UserCreateSerializer(serializers.ModelSerializer):
    """
    User oluşturmak için ayrı serializer.
    
    Neden ayrı?
    - Password field'ı sadece write için
    - Farklı validation kuralları
    """
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
    def validate_email(self, value):
        """Field-level validation."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email zaten kullanılıyor.")
        return value.lower()
    
    def validate(self, attrs):
        """Object-level validation - birden fazla field'ı kontrol et."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Şifreler eşleşmiyor."})
        return attrs
    
    def create(self, validated_data):
        """Custom create - password hash'leme için."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)  # Password'ü hash'le
        user.save()
        return user
```

**Öğrenme Noktaları:**
- `SerializerMethodField`: Hesaplanmış field, `get_<field_name>` metodu gerekir
- `write_only=True`: Sadece input'ta kabul edilir, output'ta gösterilmez
- `read_only_fields`: Sadece output'ta gösterilir, input'ta kabul edilmez
- `validate_<field_name>`: Field-level validation
- `validate`: Object-level validation (cross-field)
- `create`: Custom create logic

### Adım 2.2: Organization Serializers

**organizations/serializers.py:**
```python
from rest_framework import serializers
from .models import Organization, OrganizationMember
from users.serializers import UserSerializer


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """Organization üyeliği serializer."""
    
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = OrganizationMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Organization serializer.
    
    Nested serializer örneği.
    """
    
    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'website', 'logo',
            'owner', 'member_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'owner', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def create(self, validated_data):
        """Owner'ı request user'dan al."""
        request = self.context.get('request')
        validated_data['owner'] = request.user
        
        # Slug oluştur
        from django.utils.text import slugify
        validated_data['slug'] = slugify(validated_data['name'])
        
        org = super().create(validated_data)
        
        # Owner'ı member olarak ekle
        OrganizationMember.objects.create(
            organization=org,
            user=request.user,
            role=OrganizationMember.Role.OWNER
        )
        
        return org


class OrganizationDetailSerializer(OrganizationSerializer):
    """
    Organization detay serializer - members dahil.
    
    Neden ayrı?
    - Liste view'da members gereksiz (performans)
    - Detay view'da members gerekli
    """
    
    members = serializers.SerializerMethodField()
    
    class Meta(OrganizationSerializer.Meta):
        fields = OrganizationSerializer.Meta.fields + ['members']
    
    def get_members(self, obj):
        memberships = obj.memberships.select_related('user')
        return OrganizationMemberSerializer(memberships, many=True).data
```

**Öğrenme Noktaları:**
- Nested serializer: `owner = UserSerializer(read_only=True)`
- `self.context`: View'dan gelen context (request, view, format)
- Serializer inheritance: `OrganizationDetailSerializer(OrganizationSerializer)`
- `select_related`: N+1 query önleme

### Adım 2.3: Project Serializers

**projects/serializers.py:**
```python
from rest_framework import serializers
from .models import Project, Task, TaskComment
from users.serializers import UserSerializer
from organizations.serializers import OrganizationSerializer


class TaskCommentSerializer(serializers.ModelSerializer):
    """Task comment serializer."""
    
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = TaskComment
        fields = ['id', 'author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['author'] = request.user
        return super().create(validated_data)


class TaskSerializer(serializers.ModelSerializer):
    """Task serializer."""
    
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    created_by = UserSerializer(read_only=True)
    comment_count = serializers.SerializerMethodField()
    subtask_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'project', 'assignee', 'assignee_id',
            'created_by', 'parent', 'priority', 'status', 'due_date',
            'estimated_hours', 'comment_count', 'subtask_count',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'completed_at']
    
    def get_comment_count(self, obj):
        return obj.comments.count()
    
    def get_subtask_count(self, obj):
        return obj.subtasks.count()
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Status 'done' olunca completed_at set et."""
        from django.utils import timezone
        
        if validated_data.get('status') == Task.Status.DONE and instance.status != Task.Status.DONE:
            validated_data['completed_at'] = timezone.now()
        
        return super().update(instance, validated_data)


class TaskDetailSerializer(TaskSerializer):
    """Task detay serializer - comments ve subtasks dahil."""
    
    comments = TaskCommentSerializer(many=True, read_only=True)
    subtasks = serializers.SerializerMethodField()
    
    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['comments', 'subtasks']
    
    def get_subtasks(self, obj):
        subtasks = obj.subtasks.select_related('assignee', 'created_by')
        return TaskSerializer(subtasks, many=True, context=self.context).data


class ProjectSerializer(serializers.ModelSerializer):
    """Project serializer."""
    
    organization = OrganizationSerializer(read_only=True)
    organization_id = serializers.IntegerField(write_only=True)
    created_by = UserSerializer(read_only=True)
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'slug', 'description', 'organization', 'organization_id',
            'created_by', 'status', 'visibility', 'task_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_by', 'created_at', 'updated_at']
    
    def get_task_count(self, obj):
        return obj.tasks.count()
    
    def validate_organization_id(self, value):
        """User'ın bu org'a erişimi var mı kontrol et."""
        request = self.context.get('request')
        from organizations.models import OrganizationMember
        
        if not OrganizationMember.objects.filter(
            organization_id=value,
            user=request.user
        ).exists():
            raise serializers.ValidationError("Bu organizasyona erişiminiz yok.")
        
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        
        from django.utils.text import slugify
        validated_data['slug'] = slugify(validated_data['name'])
        
        return super().create(validated_data)


class ProjectDetailSerializer(ProjectSerializer):
    """Project detay serializer - tasks dahil."""
    
    tasks = serializers.SerializerMethodField()
    
    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ['tasks']
    
    def get_tasks(self, obj):
        # Sadece parent'ı olmayan task'ları getir (subtask'ları değil)
        tasks = obj.tasks.filter(parent__isnull=True).select_related('assignee', 'created_by')
        return TaskSerializer(tasks, many=True, context=self.context).data
```

**Öğrenme Noktaları:**
- Read/Write field pattern: `assignee` (read) + `assignee_id` (write)
- `many=True`: Liste serialization
- `context` propagation: Nested serializer'a context geçirme
- Custom `update`: Status değişikliğinde ek logic

### Adım 2.4: Validation Best Practices

```python
from rest_framework import serializers


class AdvancedValidationExample(serializers.Serializer):
    """Validation örnekleri."""
    
    # Built-in validators
    email = serializers.EmailField()
    url = serializers.URLField()
    age = serializers.IntegerField(min_value=0, max_value=150)
    
    # Regex validator
    phone = serializers.RegexField(
        regex=r'^\+?1?\d{9,15}$',
        error_messages={'invalid': 'Geçerli bir telefon numarası girin.'}
    )
    
    # Choice validator
    status = serializers.ChoiceField(choices=['active', 'inactive'])
    
    # Custom validator function
    def validate_email(self, value):
        """Field-level validation."""
        if 'spam' in value:
            raise serializers.ValidationError("Spam email'ler kabul edilmiyor.")
        return value
    
    def validate(self, attrs):
        """
        Object-level validation.
        
        Kullanım alanları:
        - Cross-field validation
        - Conditional validation
        - Business logic validation
        """
        # Örnek: start_date < end_date
        if attrs.get('start_date') and attrs.get('end_date'):
            if attrs['start_date'] > attrs['end_date']:
                raise serializers.ValidationError({
                    'end_date': 'Bitiş tarihi başlangıç tarihinden sonra olmalı.'
                })
        
        return attrs


# Reusable validator
def validate_no_profanity(value):
    """Reusable validator function."""
    profanity_list = ['badword1', 'badword2']
    for word in profanity_list:
        if word in value.lower():
            raise serializers.ValidationError("Uygunsuz içerik tespit edildi.")
    return value


class ContentSerializer(serializers.Serializer):
    title = serializers.CharField(validators=[validate_no_profanity])
    content = serializers.CharField(validators=[validate_no_profanity])
```

---

## Ödevler

### Ödev 1: Unique Together Validation
`Project` serializer'da `organization` + `name` kombinasyonunun unique olduğunu validate et.

### Ödev 2: Conditional Required Fields
`Task` serializer'da `status = 'done'` ise `completed_at` zorunlu olsun.

### Ödev 3: Nested Create
`Project` oluştururken aynı request'te `tasks` da oluşturulabilsin:
```json
{
  "name": "My Project",
  "organization_id": 1,
  "tasks": [
    {"title": "Task 1"},
    {"title": "Task 2"}
  ]
}
```

### Ödev 4: Dynamic Fields
Serializer'a `fields` query parameter'ı ekle:
```
GET /api/projects/?fields=id,name,task_count
```

---

## Kontrol Listesi

- [ ] UserSerializer oluşturuldu
- [ ] UserCreateSerializer oluşturuldu (password handling)
- [ ] OrganizationSerializer oluşturuldu
- [ ] OrganizationDetailSerializer oluşturuldu (nested members)
- [ ] TaskSerializer oluşturuldu
- [ ] TaskDetailSerializer oluşturuldu (nested comments, subtasks)
- [ ] ProjectSerializer oluşturuldu
- [ ] ProjectDetailSerializer oluşturuldu (nested tasks)
- [ ] Field-level validation anlaşıldı
- [ ] Object-level validation anlaşıldı
- [ ] Ödev 1 tamamlandı
- [ ] Ödev 2 tamamlandı
- [ ] Ödev 3 tamamlandı
- [ ] Ödev 4 tamamlandı

---

## Kaynaklar

- [DRF Serializers](https://www.django-rest-framework.org/api-guide/serializers/)
- [DRF Validators](https://www.django-rest-framework.org/api-guide/validators/)
- [Serializer Relations](https://www.django-rest-framework.org/api-guide/relations/)


---

# MODÜL 3: Views & ViewSets

## Hedef
DRF Views ve ViewSets kullanarak API endpoints oluşturmak.

## Öğreneceklerin
- APIView vs GenericAPIView vs ViewSet
- Mixins
- Custom actions
- URL routing
- Request/Response handling

## Adımlar

### Adım 3.1: URL Yapılandırması

**config/urls.py:**
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/organizations/', include('organizations.urls')),
    path('api/projects/', include('projects.urls')),
]
```

### Adım 3.2: User Views

**users/views.py:**
```python
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from .serializers import UserSerializer, UserCreateSerializer


class UserRegisterView(generics.CreateAPIView):
    """
    User registration.
    
    CreateAPIView:
    - POST method için
    - create() metodu hazır
    """
    
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]


class UserMeView(APIView):
    """
    Current user bilgisi.
    
    APIView:
    - En temel view class
    - get(), post(), put(), delete() metodlarını override et
    - Tam kontrol istediğinde kullan
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserDetailView(generics.RetrieveAPIView):
    """
    User detay - public profile.
    
    RetrieveAPIView:
    - GET method için (tek obje)
    - retrieve() metodu hazır
    """
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'username'  # Default: 'pk'
```

**users/urls.py:**
```python
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.UserRegisterView.as_view(), name='user-register'),
    path('me/', views.UserMeView.as_view(), name='user-me'),
    path('<str:username>/', views.UserDetailView.as_view(), name='user-detail'),
]
```

### Adım 3.3: Organization ViewSet

**organizations/views.py:**
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Organization, OrganizationMember
from .serializers import (
    OrganizationSerializer,
    OrganizationDetailSerializer,
    OrganizationMemberSerializer
)


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Organization CRUD.
    
    ModelViewSet:
    - list(), create(), retrieve(), update(), partial_update(), destroy() hazır
    - Router ile URL'ler otomatik oluşur
    """
    
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """
        Sadece user'ın üye olduğu organizasyonları getir.
        
        Neden get_queryset override?
        - User-specific filtering
        - Dynamic queryset
        """
        return Organization.objects.filter(
            members=self.request.user
        ).select_related('owner').prefetch_related('members')
    
    def get_serializer_class(self):
        """
        Action'a göre farklı serializer.
        
        Neden get_serializer_class override?
        - Liste için basit serializer
        - Detay için nested serializer
        """
        if self.action == 'retrieve':
            return OrganizationDetailSerializer
        return OrganizationSerializer
    
    @action(detail=True, methods=['get'])
    def members(self, request, slug=None):
        """
        Custom action: /api/organizations/{slug}/members/
        
        @action decorator:
        - detail=True: Tek obje üzerinde (/organizations/{slug}/members/)
        - detail=False: Liste üzerinde (/organizations/members/)
        """
        org = self.get_object()
        memberships = org.memberships.select_related('user')
        serializer = OrganizationMemberSerializer(memberships, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, slug=None):
        """Custom action: Üye ekle."""
        org = self.get_object()
        
        # Permission check - sadece owner/admin ekleyebilir
        membership = org.memberships.filter(user=request.user).first()
        if not membership or membership.role not in ['owner', 'admin']:
            return Response(
                {'error': 'Bu işlem için yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = OrganizationMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=org)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, slug=None, user_id=None):
        """Custom action: Üye çıkar."""
        org = self.get_object()
        
        # Owner çıkarılamaz
        if str(org.owner_id) == user_id:
            return Response(
                {'error': 'Owner organizasyondan çıkarılamaz.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership = org.memberships.filter(user_id=user_id).first()
        if not membership:
            return Response(
                {'error': 'Üye bulunamadı.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

**organizations/urls.py:**
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.OrganizationViewSet, basename='organization')

urlpatterns = [
    path('', include(router.urls)),
]
```

**Öğrenme Noktaları:**
- `ModelViewSet`: Full CRUD
- `get_queryset()`: Dynamic queryset
- `get_serializer_class()`: Dynamic serializer
- `@action`: Custom endpoints
- `detail=True/False`: Tek obje vs liste
- `url_path`: Custom URL pattern

### Adım 3.4: Project ViewSet

**projects/views.py:**
```python
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Project, Task, TaskComment
from .serializers import (
    ProjectSerializer,
    ProjectDetailSerializer,
    TaskSerializer,
    TaskDetailSerializer,
    TaskCommentSerializer
)


class ProjectViewSet(viewsets.ModelViewSet):
    """Project CRUD."""
    
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'visibility', 'organization']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """User'ın erişebildiği projeler."""
        return Project.objects.filter(
            organization__members=self.request.user
        ).select_related('organization', 'created_by')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectSerializer
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, slug=None):
        """Projenin task'ları."""
        project = self.get_object()
        tasks = project.tasks.filter(parent__isnull=True).select_related('assignee', 'created_by')
        
        # Filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        
        serializer = TaskSerializer(tasks, many=True, context={'request': request})
        return Response(serializer.data)


class TaskViewSet(viewsets.ModelViewSet):
    """Task CRUD."""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'assignee', 'project']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'priority', 'due_date', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """User'ın erişebildiği task'lar."""
        return Task.objects.filter(
            project__organization__members=self.request.user
        ).select_related('project', 'assignee', 'created_by', 'parent')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Task'ı birine ata."""
        task = self.get_object()
        user_id = request.data.get('user_id')
        
        if user_id:
            # User'ın bu projeye erişimi var mı?
            from organizations.models import OrganizationMember
            if not OrganizationMember.objects.filter(
                organization=task.project.organization,
                user_id=user_id
            ).exists():
                return Response(
                    {'error': 'Bu kullanıcı projeye erişemiyor.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            task.assignee_id = user_id
        else:
            task.assignee = None
        
        task.save()
        serializer = TaskSerializer(task, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Task status değiştir."""
        task = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Task.Status.choices):
            return Response(
                {'error': 'Geçersiz status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = new_status
        
        # Done olunca completed_at set et
        if new_status == Task.Status.DONE:
            from django.utils import timezone
            task.completed_at = timezone.now()
        
        task.save()
        serializer = TaskSerializer(task, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Task yorumları."""
        task = self.get_object()
        
        if request.method == 'GET':
            comments = task.comments.select_related('author')
            serializer = TaskCommentSerializer(comments, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = TaskCommentSerializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(task=task)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class TaskCommentViewSet(viewsets.ModelViewSet):
    """TaskComment CRUD."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = TaskCommentSerializer
    
    def get_queryset(self):
        return TaskComment.objects.filter(
            task__project__organization__members=self.request.user
        ).select_related('task', 'author')
```

**projects/urls.py:**
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('projects', views.ProjectViewSet, basename='project')
router.register('tasks', views.TaskViewSet, basename='task')
router.register('comments', views.TaskCommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]
```

### Adım 3.5: Mixins Kullanımı

```python
from rest_framework import mixins, viewsets


# Sadece list ve retrieve (read-only)
class ReadOnlyProjectViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


# Sadece create
class CreateOnlyViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    pass


# List, create, retrieve (update ve delete yok)
class LimitedViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    pass
```

**Mixin'ler:**
- `CreateModelMixin`: create()
- `ListModelMixin`: list()
- `RetrieveModelMixin`: retrieve()
- `UpdateModelMixin`: update(), partial_update()
- `DestroyModelMixin`: destroy()

---

## Ödevler

### Ödev 1: Nested Router
Task'ları project altında nested route olarak yap:
```
/api/projects/{project_slug}/tasks/
/api/projects/{project_slug}/tasks/{task_id}/
```

### Ödev 2: Bulk Actions
Birden fazla task'ın status'unu tek request'te değiştir:
```json
POST /api/tasks/bulk-status/
{
  "task_ids": [1, 2, 3],
  "status": "done"
}
```

### Ödev 3: Custom Permission
`IsProjectMember` permission class yaz - sadece proje üyeleri erişebilsin.

### Ödev 4: Throttling
Task create için rate limiting ekle: Dakikada max 10 task.

---

## Kontrol Listesi

- [ ] URL yapılandırması tamamlandı
- [ ] UserRegisterView oluşturuldu
- [ ] UserMeView oluşturuldu
- [ ] OrganizationViewSet oluşturuldu
- [ ] Custom actions eklendi (members, add_member, remove_member)
- [ ] ProjectViewSet oluşturuldu
- [ ] TaskViewSet oluşturuldu
- [ ] Filtering, searching, ordering eklendi
- [ ] Ödev 1 tamamlandı
- [ ] Ödev 2 tamamlandı
- [ ] Ödev 3 tamamlandı
- [ ] Ödev 4 tamamlandı

---

## Kaynaklar

- [DRF Views](https://www.django-rest-framework.org/api-guide/views/)
- [DRF ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/)
- [DRF Routers](https://www.django-rest-framework.org/api-guide/routers/)
- [DRF Filtering](https://www.django-rest-framework.org/api-guide/filtering/)


---

# MODÜL 4: Authentication & Authorization

## Hedef
JWT authentication ve custom permissions ile güvenli API oluşturmak.

## Öğreneceklerin
- JWT authentication (access + refresh token)
- Custom permissions
- Object-level permissions
- Role-based access control (RBAC)

## Adımlar

### Adım 4.1: JWT Kurulumu

```bash
pip install djangorestframework-simplejwt
```

**config/settings.py:**
```python
from datetime import timedelta

INSTALLED_APPS = [
    # ...
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

**config/urls.py:**
```python
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # ...
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

### Adım 4.2: Custom Permissions

**core/permissions.py:**
```python
from rest_framework import permissions
from organizations.models import OrganizationMember


class IsOwner(permissions.BasePermission):
    """
    Object owner'ı mı kontrol et.
    
    Kullanım: Model'de 'owner' veya 'created_by' field'ı olmalı.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions - herkese açık
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions - sadece owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False


class IsOrganizationMember(permissions.BasePermission):
    """
    User organizasyon üyesi mi kontrol et.
    """
    
    def has_permission(self, request, view):
        # Organization ID'yi nereden alacağız?
        org_slug = view.kwargs.get('organization_slug')
        org_id = request.data.get('organization_id') or request.query_params.get('organization')
        
        if org_slug:
            return OrganizationMember.objects.filter(
                organization__slug=org_slug,
                user=request.user
            ).exists()
        
        if org_id:
            return OrganizationMember.objects.filter(
                organization_id=org_id,
                user=request.user
            ).exists()
        
        return True  # Org belirtilmemişse geç
    
    def has_object_permission(self, request, view, obj):
        # Object'in organization'ını bul
        org = None
        if hasattr(obj, 'organization'):
            org = obj.organization
        elif hasattr(obj, 'project'):
            org = obj.project.organization
        elif hasattr(obj, 'task'):
            org = obj.task.project.organization
        
        if org:
            return OrganizationMember.objects.filter(
                organization=org,
                user=request.user
            ).exists()
        
        return False


class IsOrganizationAdmin(permissions.BasePermission):
    """
    User organizasyon admin'i mi kontrol et.
    """
    
    def has_object_permission(self, request, view, obj):
        org = None
        if hasattr(obj, 'organization'):
            org = obj.organization
        elif isinstance(obj, Organization):
            org = obj
        
        if org:
            return OrganizationMember.objects.filter(
                organization=org,
                user=request.user,
                role__in=['owner', 'admin']
            ).exists()
        
        return False


class IsProjectMember(permissions.BasePermission):
    """
    User proje üyesi mi kontrol et.
    
    Proje üyeliği = Organizasyon üyeliği (bu projede)
    """
    
    def has_object_permission(self, request, view, obj):
        project = None
        if hasattr(obj, 'project'):
            project = obj.project
        elif isinstance(obj, Project):
            project = obj
        
        if project:
            return OrganizationMember.objects.filter(
                organization=project.organization,
                user=request.user
            ).exists()
        
        return False


class IsTaskAssignee(permissions.BasePermission):
    """
    User task'a atanmış mı kontrol et.
    """
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'assignee'):
            return obj.assignee == request.user
        return False
```

### Adım 4.3: Permission Kullanımı

**projects/views.py:**
```python
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsOrganizationMember, IsOwner


class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    
    def get_permissions(self):
        """
        Action'a göre farklı permission.
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            # Sadece owner düzenleyebilir/silebilir
            return [IsAuthenticated(), IsOwner()]
        return super().get_permissions()


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    
    def get_permissions(self):
        if self.action == 'destroy':
            # Sadece task oluşturan silebilir
            return [IsAuthenticated(), IsOwner()]
        if self.action in ['assign', 'change_status']:
            # Assignee veya proje üyesi değiştirebilir
            return [IsAuthenticated(), IsOrganizationMember()]
        return super().get_permissions()
```

### Adım 4.4: Role-Based Access Control (RBAC)

**core/permissions.py (devam):**
```python
class RoleBasedPermission(permissions.BasePermission):
    """
    Role-based permission.
    
    Kullanım:
    class MyView(APIView):
        permission_classes = [RoleBasedPermission]
        required_roles = ['owner', 'admin']
    """
    
    def has_permission(self, request, view):
        required_roles = getattr(view, 'required_roles', [])
        
        if not required_roles:
            return True
        
        # Organization'ı bul
        org_slug = view.kwargs.get('slug') or view.kwargs.get('organization_slug')
        
        if org_slug:
            membership = OrganizationMember.objects.filter(
                organization__slug=org_slug,
                user=request.user
            ).first()
            
            if membership:
                return membership.role in required_roles
        
        return False


# Kullanım örneği
class OrganizationSettingsView(APIView):
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    required_roles = ['owner', 'admin']
    
    def get(self, request, slug):
        # Sadece owner ve admin erişebilir
        pass
```

### Adım 4.5: Custom Token Claims

**users/serializers.py:**
```python
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Token'a ekstra bilgi ekle.
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Response'a ekstra bilgi ekle
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
        }
        
        return data
```

**users/views.py:**
```python
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
```

---

## Ödevler

### Ödev 1: Token Blacklist
Logout endpoint'i yap - refresh token'ı blacklist'e ekle.

### Ödev 2: Permission Hierarchy
Organization role hierarchy implement et:
- Owner > Admin > Member > Viewer
- Üst role, alt role'ün tüm yetkilerine sahip

### Ödev 3: Resource-Level Permissions
Task için detaylı permission:
- Viewer: Sadece okuyabilir
- Member: Task oluşturabilir, kendi task'larını düzenleyebilir
- Admin: Tüm task'ları düzenleyebilir
- Owner: Her şeyi yapabilir

### Ödev 4: API Key Authentication
Service-to-service iletişim için API key authentication ekle.

---

## Kontrol Listesi

- [ ] JWT kurulumu tamamlandı
- [ ] Token endpoint'leri çalışıyor
- [ ] IsOwner permission oluşturuldu
- [ ] IsOrganizationMember permission oluşturuldu
- [ ] IsOrganizationAdmin permission oluşturuldu
- [ ] View'larda permission kullanıldı
- [ ] Custom token claims eklendi
- [ ] Ödev 1 tamamlandı
- [ ] Ödev 2 tamamlandı
- [ ] Ödev 3 tamamlandı
- [ ] Ödev 4 tamamlandı

---

# MODÜL 5-15: İleri Seviye Konular

## Modül 5: Filtering, Searching, Ordering
- django-filter integration
- Full-text search (PostgreSQL)
- Custom filter backends

## Modül 6: Pagination & Caching
- Cursor pagination
- Redis caching
- Cache invalidation

## Modül 7: Background Tasks
- Celery integration
- Email notifications
- Scheduled tasks

## Modül 8: File Handling
- S3 integration
- Presigned URLs
- Image processing

## Modül 9: Real-time Features
- Django Channels
- WebSocket
- Notifications

## Modül 10: API Design & Documentation
- OpenAPI/Swagger
- API versioning
- Rate limiting

## Modül 11: Testing
- pytest
- Factory Boy
- Coverage

## Modül 12: Security
- Input validation
- CORS
- Security headers

## Modül 13: Performance
- Query optimization
- Async views
- Load testing

## Modül 14: Deployment
- Docker
- CI/CD
- Environment management

## Modül 15: Monitoring
- Logging
- Metrics
- Alerting

---

# Genel Tavsiyeler

## Öğrenme Yaklaşımı

1. **Önce oku, sonra yaz**: Her modülü okumadan koda başlama
2. **Kopyala-yapıştır yapma**: Kodu anlayarak yaz
3. **Hata yap**: Hatalar en iyi öğretmendir
4. **Debug et**: print() yerine debugger kullan
5. **Test yaz**: Her feature için test

## Kod Kalitesi

1. **PEP 8**: Python style guide'a uy
2. **Type hints**: Fonksiyonlara type hint ekle
3. **Docstrings**: Her class ve fonksiyona docstring yaz
4. **DRY**: Kendini tekrar etme
5. **SOLID**: SOLID prensiplerini uygula

## Git Workflow

1. **Feature branch**: Her feature için ayrı branch
2. **Commit messages**: Anlamlı commit mesajları
3. **Pull request**: Kendi kodunu review et
4. **Merge**: Squash merge kullan

## Kaynaklar

### Dokümantasyon
- [Django Documentation](https://docs.djangoproject.com/)
- [DRF Documentation](https://www.django-rest-framework.org/)
- [Python Documentation](https://docs.python.org/3/)

### Kitaplar
- Two Scoops of Django
- Django for Professionals
- Architecture Patterns with Python

### Kurslar
- Django for Everybody (Coursera)
- REST APIs with Django (Real Python)

### Bloglar
- Real Python
- Simple is Better Than Complex
- Django Stars

---

# Son Söz

Bu proje seni junior'dan senior'a taşıyacak. Acele etme, her modülü sindire sindire öğren. Takıldığın yerde:

1. Önce dokümantasyonu oku
2. Stack Overflow'da ara
3. ChatGPT/Claude'a sor
4. Topluluk forumlarına yaz

Başarılar! 🚀
