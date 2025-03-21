register(QUICKREPORT,
         id    = 'NumberOfDescendantsQuickview',
         name  = _("Number of descendants"),
         description= _("Shows the number of descendants of the current person"),
         version = '3.4.31',
         gramps_target_version = "5.2",
         status = STABLE,
         fname = 'NumberOfDescendantsQuickview.py',
         authors = ["Reinhard Mueller"],
         authors_email = ["reinhard.mueller@igal.at"],
         category = CATEGORY_QR_PERSON,
         runfunc = 'run')
