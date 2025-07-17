# Call Audit Backend



## Migrations commands:


```bash
# first this one
alembic revision --autogenerate -m "Migration message"

# then generate migrations:
alembic upgrade head
```


## Sample accounts

```
Managers:
  Email: john.smith@company.com, Password: manager123
  Email: sarah.johnson@company.com, Password: manager123

Auditors:
  Email: mike.wilson@company.com, Password: auditor123
  Email: lisa.chen@company.com, Password: auditor123
  Email: david.brown@company.com, Password: auditor123
  Email: emma.davis@company.com, Password: auditor123
```
