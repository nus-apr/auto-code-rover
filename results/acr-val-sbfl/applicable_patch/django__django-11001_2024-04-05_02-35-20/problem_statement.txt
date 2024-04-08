Incorrect removal of order_by clause created as multiline RawSQL
Description
	
Hi.
The SQLCompiler is ripping off one of my "order by" clause, because he "thinks" the clause was already "seen" (in SQLCompiler.get_order_by()). I'm using expressions written as multiline RawSQLs, which are similar but not the same. 
The bug is located in SQLCompiler.get_order_by(), somewhere around line computing part of SQL query without ordering:
without_ordering = self.ordering_parts.search(sql).group(1)
The sql variable contains multiline sql. As a result, the self.ordering_parts regular expression is returning just a line containing ASC or DESC words. This line is added to seen set, and because my raw queries have identical last lines, only the first clasue is returing from SQLCompiler.get_order_by().
As a quick/temporal fix I can suggest making sql variable clean of newline characters, like this:
sql_oneline = ' '.join(sql.split('\n'))
without_ordering = self.ordering_parts.search(sql_oneline).group(1)
Note: beware of unicode (Py2.x u'') and EOL dragons (\r).
Example of my query:
	return MyModel.objects.all().order_by(
		RawSQL('''
			case when status in ('accepted', 'verification')
				 then 2 else 1 end''', []).desc(),
		RawSQL('''
			case when status in ('accepted', 'verification')
				 then (accepted_datetime, preferred_datetime)
				 else null end''', []).asc(),
		RawSQL('''
			case when status not in ('accepted', 'verification')
				 then (accepted_datetime, preferred_datetime, created_at)
				 else null end''', []).desc())
The ordering_parts.search is returing accordingly:
'				 then 2 else 1 end)'
'				 else null end'
'				 else null end'
Second RawSQL with a				 else null end part is removed from query.
The fun thing is that the issue can be solved by workaround by adding a space or any other char to the last line. 
So in case of RawSQL I can just say, that current implementation of avoiding duplicates in order by clause works only for special/rare cases (or does not work in all cases). 
The bug filed here is about wrong identification of duplicates (because it compares only last line of SQL passed to order by clause).
Hope my notes will help you fixing the issue. Sorry for my english.
