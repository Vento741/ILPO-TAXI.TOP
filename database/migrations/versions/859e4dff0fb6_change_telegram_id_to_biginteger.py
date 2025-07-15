"""Change telegram_id to BigInteger

Revision ID: 859e4dff0fb6
Revises: 
Create Date: 2025-07-15 13:41:29.837324

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '859e4dff0fb6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create managers table first (referenced by applications)
    op.create_table('managers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False, comment='Telegram ID менеджера'),
        sa.Column('username', sa.String(length=100), nullable=True, comment='Telegram username'),
        sa.Column('first_name', sa.String(length=100), nullable=False, comment='Имя'),
        sa.Column('last_name', sa.String(length=100), nullable=True, comment='Фамилия'),
        sa.Column('status', sa.Enum('ONLINE', 'BUSY', 'OFFLINE', name='managerstatus'), nullable=True, comment='Статус менеджера'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='Активен ли менеджер'),
        sa.Column('is_admin', sa.Boolean(), nullable=True, comment='Является ли администратором'),
        sa.Column('max_active_chats', sa.Integer(), nullable=True, comment='Максимум активных чатов'),
        sa.Column('total_applications', sa.Integer(), nullable=True, comment='Всего обработано заявок'),
        sa.Column('avg_response_time', sa.Integer(), nullable=True, comment='Среднее время ответа в секундах'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='Время регистрации'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True, comment='Последняя активность'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id'),
        comment='Модель менеджера поддержки'
    )
    op.create_index(op.f('ix_managers_id'), 'managers', ['id'], unique=False)

    # Create applications table
    op.create_table('applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False, comment='ФИО клиента'),
        sa.Column('phone', sa.String(length=20), nullable=False, comment='Телефон клиента'),
        sa.Column('age', sa.Integer(), nullable=True, comment='Возраст'),
        sa.Column('city', sa.String(length=100), nullable=False, comment='Город'),
        sa.Column('category', sa.String(length=50), nullable=False, comment='Категория: driver, courier, both, cargo'),
        sa.Column('experience', sa.String(length=50), nullable=True, comment='Стаж вождения'),
        sa.Column('transport', sa.String(length=50), nullable=True, comment='Вид транспорта для курьеров'),
        sa.Column('load_capacity', sa.String(length=50), nullable=True, comment='Грузоподъемность'),
        sa.Column('additional_info', sa.Text(), nullable=True, comment='Дополнительная информация'),
        sa.Column('status', sa.Enum('NEW', 'ASSIGNED', 'IN_PROGRESS', 'WAITING_CLIENT', 'COMPLETED', 'CANCELLED', name='applicationstatus'), nullable=True, comment='Статус заявки'),
        sa.Column('assigned_manager_id', sa.Integer(), nullable=True, comment='Назначенный менеджер'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Заметки менеджера'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='Время создания'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='Время обновления'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True, comment='Время обработки'),
        sa.ForeignKeyConstraint(['assigned_manager_id'], ['managers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='Модель заявки с сайта'
    )
    op.create_index(op.f('ix_applications_id'), 'applications', ['id'], unique=False)



    # Create support_chats table
    op.create_table('support_chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.String(length=100), nullable=False, comment='Уникальный ID чата'),
        sa.Column('chat_type', sa.Enum('WEB_CHAT', 'TELEGRAM_DIRECT', 'TRANSFER_FROM_AI', name='chattype'), nullable=False, comment='Тип чата'),
        sa.Column('client_telegram_id', sa.BigInteger(), nullable=True, comment='Telegram ID клиента'),
        sa.Column('client_name', sa.String(length=200), nullable=True, comment='Имя клиента'),
        sa.Column('client_phone', sa.String(length=20), nullable=True, comment='Телефон клиента'),
        sa.Column('manager_id', sa.Integer(), nullable=True, comment='Назначенный менеджер'),
        sa.Column('application_id', sa.Integer(), nullable=True, comment='Связанная заявка'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='Активен ли чат'),
        sa.Column('is_ai_handed_over', sa.Boolean(), nullable=True, comment='Передан ли от ИИ'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='Время создания'),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True, comment='Время закрытия'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True, comment='Время последнего сообщения'),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Теги чата'),
        sa.Column('chat_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Дополнительные метаданные'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.ForeignKeyConstraint(['manager_id'], ['managers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id'),
        comment='Модель чата поддержки'
    )
    op.create_index(op.f('ix_support_chats_id'), 'support_chats', ['id'], unique=False)

    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False, comment='ID чата'),
        sa.Column('sender_type', sa.String(length=20), nullable=False, comment='client, manager, system'),
        sa.Column('sender_telegram_id', sa.BigInteger(), nullable=True, comment='Telegram ID отправителя'),
        sa.Column('sender_name', sa.String(length=200), nullable=True, comment='Имя отправителя'),
        sa.Column('message_text', sa.Text(), nullable=False, comment='Текст сообщения'),
        sa.Column('message_type', sa.String(length=20), nullable=True, comment='Тип: text, photo, document, etc.'),
        sa.Column('file_url', sa.String(length=500), nullable=True, comment='URL файла если есть'),
        sa.Column('telegram_message_id', sa.String(length=50), nullable=True, comment='ID сообщения в Telegram'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='Время отправки'),
        sa.Column('is_read', sa.Boolean(), nullable=True, comment='Прочитано ли сообщение'),
        sa.ForeignKeyConstraint(['chat_id'], ['support_chats.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='Модель сообщения в чате поддержки'
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)

    # Create manager_work_sessions table
    op.create_table('manager_work_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('manager_id', sa.Integer(), nullable=False, comment='ID менеджера'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='Начало сессии'),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True, comment='Конец сессии'),
        sa.Column('applications_processed', sa.Integer(), nullable=True, comment='Обработано заявок'),
        sa.Column('chats_handled', sa.Integer(), nullable=True, comment='Обработано чатов'),
        sa.Column('avg_response_time', sa.Integer(), nullable=True, comment='Среднее время ответа'),
        sa.ForeignKeyConstraint(['manager_id'], ['managers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='Модель рабочей сессии менеджера'
    )
    op.create_index(op.f('ix_manager_work_sessions_id'), 'manager_work_sessions', ['id'], unique=False)

    # Create indexes for optimization
    op.create_index('idx_applications_status', 'applications', ['status'], unique=False)
    op.create_index('idx_applications_created', 'applications', ['created_at'], unique=False)
    op.create_index('idx_applications_phone', 'applications', ['phone'], unique=False)
    op.create_index('idx_managers_telegram_id', 'managers', ['telegram_id'], unique=False)
    op.create_index('idx_managers_status', 'managers', ['status'], unique=False)
    op.create_index('idx_support_chats_active', 'support_chats', ['is_active'], unique=False)
    op.create_index('idx_support_chats_manager', 'support_chats', ['manager_id'], unique=False)
    op.create_index('idx_support_chats_created', 'support_chats', ['created_at'], unique=False)
    op.create_index('idx_chat_messages_chat', 'chat_messages', ['chat_id'], unique=False)
    op.create_index('idx_chat_messages_created', 'chat_messages', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_chat_messages_created', table_name='chat_messages')
    op.drop_index('idx_chat_messages_chat', table_name='chat_messages')
    op.drop_index('idx_support_chats_created', table_name='support_chats')
    op.drop_index('idx_support_chats_manager', table_name='support_chats')
    op.drop_index('idx_support_chats_active', table_name='support_chats')
    op.drop_index('idx_managers_status', table_name='managers')
    op.drop_index('idx_managers_telegram_id', table_name='managers')
    op.drop_index('idx_applications_phone', table_name='applications')
    op.drop_index('idx_applications_created', table_name='applications')
    op.drop_index('idx_applications_status', table_name='applications')
    
    # Drop tables in reverse order (tables with foreign keys first)
    op.drop_table('manager_work_sessions')
    op.drop_table('chat_messages')
    op.drop_table('support_chats')
    op.drop_table('applications')  # Drop applications before managers (has FK to managers)
    op.drop_table('managers')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS applicationstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS managerstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS chattype CASCADE') 