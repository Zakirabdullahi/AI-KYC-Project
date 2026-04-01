import traceback
try:
    import seed_admin
    seed_admin.create_admin()
except Exception as e:
    with open('seed_error.txt', 'w') as f:
        f.write(traceback.format_exc())
