<?php
header('Content-type: text/plain');
echo file_get_contents('http://tools-elastic-01/?pretty');
echo "\n";
echo file_get_contents('http://tools-elastic-01/_cluster/health?pretty');
echo "\n";
echo file_get_contents('http://tools-elastic-01/_cat/nodes?v&s=name');
echo "\n";
echo file_get_contents('http://tools-elastic-01/_cat/indices?v&s=index');
