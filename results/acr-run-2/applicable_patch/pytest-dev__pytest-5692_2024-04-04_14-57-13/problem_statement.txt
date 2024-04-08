Hostname and timestamp properties in generated JUnit XML reports
Pytest enables generating JUnit XML reports of the tests.

However, there are some properties missing, specifically `hostname` and `timestamp` from the `testsuite` XML element. Is there an option to include them?

Example of a pytest XML report:
```xml
<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="0" failures="2" name="check" skipped="0" tests="4" time="0.049">
	<testcase classname="test_sample.TestClass" file="test_sample.py" line="3" name="test_addOne_normal" time="0.001"></testcase>
	<testcase classname="test_sample.TestClass" file="test_sample.py" line="6" name="test_addOne_edge" time="0.001"></testcase>
</testsuite>
```

Example of a junit XML report:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="location.GeoLocationTest" tests="2" skipped="0" failures="0" errors="0" timestamp="2019-04-22T10:32:27" hostname="Anass-MacBook-Pro.local" time="0.048">
  <properties/>
  <testcase name="testIoException()" classname="location.GeoLocationTest" time="0.044"/>
  <testcase name="testJsonDeserialization()" classname="location.GeoLocationTest" time="0.003"/>
  <system-out><![CDATA[]]></system-out>
  <system-err><![CDATA[]]></system-err>
</testsuite>
```
