"""Add detailed application fields from signup form

Revision ID: 20250116_001
Revises: 
Create Date: 2025-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20250116_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляем новые поля в таблицу applications"""
    
    # Добавляем новые основные поля
    op.add_column('applications', sa.Column('email', sa.String(255), nullable=True, comment='Email клиента'))
    op.add_column('applications', sa.Column('citizenship', sa.String(50), nullable=True, comment='Гражданство: rf, eaeu, other'))
    op.add_column('applications', sa.Column('work_status', sa.String(100), nullable=True, comment='Предпочитаемый статус работы'))
    op.add_column('applications', sa.Column('preferred_time', sa.String(50), nullable=True, comment='Удобное время для звонка'))
    op.add_column('applications', sa.Column('work_schedule', sa.String(100), nullable=True, comment='Предпочитаемый график работы'))
    op.add_column('applications', sa.Column('comments', sa.Text, nullable=True, comment='Дополнительные комментарии'))
    
    # Информация для водителей (расширенная)
    op.add_column('applications', sa.Column('has_driver_license', sa.String(50), nullable=True, comment='Наличие водительских прав'))
    op.add_column('applications', sa.Column('has_car', sa.String(50), nullable=True, comment='Наличие автомобиля'))
    op.add_column('applications', sa.Column('car_brand', sa.String(100), nullable=True, comment='Марка автомобиля'))
    op.add_column('applications', sa.Column('car_model', sa.String(100), nullable=True, comment='Модель автомобиля'))
    op.add_column('applications', sa.Column('car_year', sa.Integer, nullable=True, comment='Год выпуска автомобиля'))
    op.add_column('applications', sa.Column('car_class', sa.String(50), nullable=True, comment='Желаемый класс автомобиля'))
    op.add_column('applications', sa.Column('has_taxi_permit', sa.String(50), nullable=True, comment='Наличие разрешения на такси'))
    
    # Информация для курьеров (расширенная)
    op.add_column('applications', sa.Column('delivery_types', sa.JSON, nullable=True, comment='Категории доставки (массив)'))
    op.add_column('applications', sa.Column('has_thermo_bag', sa.String(50), nullable=True, comment='Наличие термосумки'))
    op.add_column('applications', sa.Column('courier_license', sa.String(50), nullable=True, comment='Права для автокурьеров'))
    
    # Информация для грузовых перевозок (расширенная)
    op.add_column('applications', sa.Column('truck_type', sa.String(50), nullable=True, comment='Тип кузова'))
    op.add_column('applications', sa.Column('cargo_license', sa.String(50), nullable=True, comment='Права на грузовой транспорт'))
    
    # Документы и опыт (новые поля)
    op.add_column('applications', sa.Column('work_experience', sa.String(100), nullable=True, comment='Опыт работы в такси/доставке'))
    op.add_column('applications', sa.Column('previous_platforms', sa.String(255), nullable=True, comment='Предыдущие платформы работы'))
    op.add_column('applications', sa.Column('has_medical_cert', sa.String(50), nullable=True, comment='Наличие медицинской справки'))
    op.add_column('applications', sa.Column('available_documents', sa.JSON, nullable=True, comment='Имеющиеся документы (массив)'))
    
    # Согласия (новые поля)
    op.add_column('applications', sa.Column('has_documents_confirmed', sa.Boolean, default=False, comment='Подтвердил наличие документов'))
    op.add_column('applications', sa.Column('agree_terms', sa.Boolean, default=False, comment='Согласие с условиями работы'))
    op.add_column('applications', sa.Column('agree_marketing', sa.Boolean, default=False, comment='Согласие на рассылку'))


def downgrade() -> None:
    """Удаляем добавленные поля"""
    
    # Удаляем новые основные поля
    op.drop_column('applications', 'email')
    op.drop_column('applications', 'citizenship')
    op.drop_column('applications', 'work_status')
    op.drop_column('applications', 'preferred_time')
    op.drop_column('applications', 'work_schedule')
    op.drop_column('applications', 'comments')
    
    # Информация для водителей
    op.drop_column('applications', 'has_driver_license')
    op.drop_column('applications', 'has_car')
    op.drop_column('applications', 'car_brand')
    op.drop_column('applications', 'car_model')
    op.drop_column('applications', 'car_year')
    op.drop_column('applications', 'car_class')
    op.drop_column('applications', 'has_taxi_permit')
    
    # Информация для курьеров
    op.drop_column('applications', 'delivery_types')
    op.drop_column('applications', 'has_thermo_bag')
    op.drop_column('applications', 'courier_license')
    
    # Информация для грузовых
    op.drop_column('applications', 'truck_type')
    op.drop_column('applications', 'cargo_license')
    
    # Документы и опыт
    op.drop_column('applications', 'work_experience')
    op.drop_column('applications', 'previous_platforms')
    op.drop_column('applications', 'has_medical_cert')
    op.drop_column('applications', 'available_documents')
    
    # Согласия
    op.drop_column('applications', 'has_documents_confirmed')
    op.drop_column('applications', 'agree_terms')
    op.drop_column('applications', 'agree_marketing') 