<?php
header('Content-type: text/plain');
echo file_get_contents('http://elasticsearch.svc.tools.eqiad1.wikimedia.cloud/?pretty');
echo "\n";
echo file_get_contents('http://elasticsearch.svc.tools.eqiad1.wikimedia.cloud/_cluster/health?pretty');
