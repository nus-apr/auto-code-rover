Squashing migrations with Meta.index_together -> indexes transition should remove deprecation warnings.
Description
	
Squashing migrations with Meta.index_together -> Meta.indexes transition should remove deprecation warnings. As far as I'm aware, it's a 4.2 release blocker because you cannot get rid of the index_together deprecation warnings without rewriting migrations, see comment.
