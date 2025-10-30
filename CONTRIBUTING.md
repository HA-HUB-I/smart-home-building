# Contributing to WebPortal

🎉 Благодарим за интереса към участие в развитието на WebPortal! Този документ описва как да допринесете за проекта.

## 📋 Кодекс на поведение

Този проект се придържа към стандартите за професионално и уважително поведение. Моля, бъдете:

- 🤝 Уважителни към другите участници
- 💡 Конструктивни в обратната връзка
- 🌍 Приветливи към нови участници
- 📚 Готови да учите и споделяте знания

## 🚀 Как да допринесете

### 1. Докладване на проблеми (Issues)

Ако откриете проблем:

1. **Проверете** дали проблемът не е вече докладван
2. **Използвайте** подходящия template за issue
3. **Опишете** стъпките за възпроизвеждане
4. **Включете** информация за системата (OS, Python версия, etc.)

### 2. Feature Requests

За нови функционалности:

1. **Опишете** проблема, който решава
2. **Обяснете** защо е полезна за потребителите
3. **Предложете** възможна имплементация
4. **Добавете** mockup-и или диаграми ако е приложимо

### 3. Code Contributions

#### Workflow

1. **Fork** на repository-то
2. **Създайте** feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** промените: `git commit -m 'Add amazing feature'`
4. **Push** към branch-а: `git push origin feature/amazing-feature`
5. **Отворете** Pull Request

#### Branch naming

- `feature/description` - нови функционалности
- `bugfix/description` - поправки на грешки
- `hotfix/description` - критични поправки
- `docs/description` - документация
- `refactor/description` - рефакториране

### 4. Code Style

#### Python Code Style

```python
# Използваме Black за форматиране
black app/ tests/

# PEP 8 compliance
flake8 app/ tests/

# Type hints
from typing import Optional, List, Dict

def process_data(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Process data with proper type hints."""
    pass
```

#### Commit Messages

Следваме [Conventional Commits](https://www.conventionalcommits.org/) формата:

```
type(scope): description

feat(auth): add password reset functionality
fix(finance): resolve calculation error in expense allocation
docs(readme): update installation instructions
refactor(models): improve database query performance
```

Types:
- `feat` - нова функционалност
- `fix` - поправка на грешка
- `docs` - документация
- `style` - форматиране
- `refactor` - рефакториране
- `test` - тестове
- `chore` - maintenance

#### Python Conventions

```python
# Класове с PascalCase
class ExpenseManager:
    pass

# Функции и променливи с snake_case
def calculate_monthly_fee():
    total_amount = 0
    
# Константи с UPPER_CASE
MAX_UPLOAD_SIZE = 16 * 1024 * 1024

# Private методи с underscore
def _internal_method(self):
    pass
```

## 🧪 Тестване

### Изпълнение на тестове

```bash
# Всички тестове
python -m pytest

# Конкретен модул
python -m pytest tests/test_auth.py

# С coverage
python -m pytest --cov=app --cov-report=html

# Verbose mode
python -m pytest -v
```

### Писане на тестове

```python
import pytest
from app import create_app, db
from app.models.user import User

class TestUserModel:
    def test_user_creation(self):
        """Test user creation with valid data."""
        user = User(
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        assert user.email == "test@example.com"
        assert user.get_full_name() == "Test User"
    
    def test_password_hashing(self):
        """Test password hashing functionality."""
        user = User()
        user.set_password("testpass123")
        
        assert user.password_hash is not None
        assert user.check_password("testpass123")
        assert not user.check_password("wrongpass")
```

### Test Requirements

- ✅ Всички нови функции трябва да имат тестове
- ✅ Поддържайте минимум 80% code coverage
- ✅ Тестовете трябва да са независими
- ✅ Използвайте fixtures за общи setup операции

## 📚 Документация

### Docstrings

```python
def calculate_expense_allocation(
    expense_amount: float,
    allocation_method: AllocationMethodEnum,
    building_units: List[Unit]
) -> Dict[int, float]:
    """
    Calculate expense allocation for building units.
    
    Args:
        expense_amount: Total expense amount to allocate
        allocation_method: Method to use for allocation
        building_units: List of units in the building
        
    Returns:
        Dictionary mapping unit_id to allocated amount
        
    Raises:
        ValueError: If expense_amount is negative
        ValueError: If building_units is empty
        
    Example:
        >>> units = [Unit(id=1, area=50), Unit(id=2, area=75)]
        >>> calculate_expense_allocation(100.0, AllocationMethodEnum.SHARES, units)
        {1: 40.0, 2: 60.0}
    """
```

### README Updates

При добавяне на нови функции, обновете:

- Списъка с функционалности
- Инструкциите за инсталация (ако е необходимо)
- Примери за използване
- API документацията

## 🗄️ Database Changes

### Migration Process

1. **Направете** промени в model файловете
2. **Генерирайте** миграция: `flask db migrate -m "Description"`
3. **Прегледайте** генерираната миграция
4. **Тествайте** миграцията локално
5. **Включете** миграцията в commit-а

### Migration Guidelines

```python
# migration_file.py
def upgrade():
    # Добавяне на нови колони с default стойности
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
    
    # Създаване на нови таблици
    op.create_table(
        'expense_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        # ...
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    # Винаги включвайте downgrade операции
    op.drop_table('expense_categories')
    op.drop_column('users', 'phone')
```

## 🎨 Frontend Contributions

### HTML/CSS Guidelines

```html
<!-- Използвайте Bootstrap 5 класове -->
<div class="container-fluid">
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <!-- Content -->
                </div>
            </div>
        </div>
    </div>
</div>
```

### JavaScript Guidelines

```javascript
// Използвайте ES6+ синтакс
const handleFormSubmission = (formData) => {
    // Валидация
    if (!formData.email) {
        showAlert('Email е задължителен', 'error');
        return false;
    }
    
    // AJAX заявка
    fetch('/api/endpoint', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        showAlert('Успешно запазено!', 'success');
    })
    .catch(error => {
        showAlert('Възникна грешка', 'error');
    });
};
```

## 🚀 Release Process

### Version Numbering

Следваме [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH` (напр. 1.2.3)
- `MAJOR` - breaking changes
- `MINOR` - нови функционалности (backward compatible)
- `PATCH` - bug fixes

### Release Checklist

- [ ] Всички тестове преминават
- [ ] Documentation е обновена
- [ ] CHANGELOG.md е актуален
- [ ] Migration файловете са тествани
- [ ] Performance impact е оценен
- [ ] Security review е направен

## 📝 Templates

### Issue Template

```markdown
## Описание на проблема
Кратко описание на проблема...

## Стъпки за възпроизвеждане
1. Отидете на '...'
2. Кликнете на '...'
3. Вижте грешката

## Очакван резултат
Описание на очаквания резултат...

## Действителен резултат
Описание на действителния резултат...

## Системна информация
- OS: [напр. Ubuntu 22.04]
- Python версия: [напр. 3.11.5]
- Browser: [напр. Chrome 118]
```

### Pull Request Template

```markdown
## Описание
Кратко описание на промените...

## Тип на промяната
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Тестване
- [ ] Тестовете преминават локално
- [ ] Добавени са нови тестове
- [ ] Manual testing е направен

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review на кода
- [ ] Документацията е обновена
- [ ] Няма merge conflicts
```

## 🤝 Community

### Комуникация

- 💬 **Discussions**: За общи въпроси и идеи
- 🐛 **Issues**: За bug reports и feature requests
- 📧 **Email**: За чувствителни въпроси

### Признание

Всички contributors ще бъдат добавени в:
- README.md contributors секция
- CHANGELOG.md за значими contributions
- Благодарности в release notes

---

**Благодарим ви за приноса към WebPortal! 🎉**