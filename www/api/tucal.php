<?php

require "../.php/session.php";

try {
    $info = $_SERVER['PATH_INFO'] ?? '';

    header('Content-Type: application/json; charset=UTF-8');
    header("Cache-Control: private, no-cache");

    switch ($info) {
        case '/rooms': rooms(); break;
        case '/calendar': calendar(); break;
        case '/job': job(); break;
        case '/courses': courses(); break;
        default: error(404);
    }
} catch (Exception $e) {
    error(500, $e->getMessage(), $e instanceof PDOException);
}

function error(int $status, string $message = null, bool $db_error = false) {
    $content = '{"status":"error","message":' . json_encode($message, JSON_FLAGS) .'}' . "\n";
    header("Status: $status");
    header("Content-Length: " . strlen($content));
    echo $content;
    tucal_exit($db_error);
}

function rooms() {
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    header("Cache-Control: public, max-age=86400");

    $res = db_exec("SELECT r.room_nr, r.room_code, r.tiss_code, r.room_name, r.room_suffix, r.room_name_short,
                  r.room_alt_name, r.room_name_normal, lt.room_code AS lt_room_code, lt.lt_name
                  FROM tucal.v_room r LEFT JOIN tucal.v_lecture_tube lt ON lt.room_nr = r.room_nr");
    $arr = $res->fetchAll();

    $content = '{"status":"success","message":null,"data":{"rooms":[' . "\n";
    for ($i = 0; $i < sizeof($arr); $i++) {
        $row = $arr[$i];
        $data = [
            "nr" => (int) $row["room_nr"],
            "room_codes" => explode('/', $row["room_code"]),
            "tiss_code" => $row["tiss_code"],
            "name" => $row["room_name"],
            "suffix" => $row["room_suffix"],
            "name_short" => $row["room_name_short"],
            "alt_name" => $row["room_alt_name"],
            "name_normalized" => $row["room_name_normal"],
            "lt_room_code" => $row["lt_room_code"],
            "lt_name" => $row["lt_name"],
        ];
        $content .= json_encode($data, JSON_FLAGS);
        if ($i !== sizeof($arr) - 1) $content .= ",";
        $content .= "\n";
    }
    $content .= "]}}\n";
    header("Content-Length: " . strlen($content));
    echo $content;
    tucal_exit();
}

function job() {
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    $jobId = $_GET['id'] ?? null;

    if ($jobId === null) {
        error(400, "missing field 'id'");
    }

    $stmt = db_exec("SELECT data, status FROM tucal.v_job WHERE job_id = ?", [$jobId]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) === 0) {
        error(404);
    }

    echo '{"status":"success","message":"work in progress","data":' . "\n";
    $data = json_decode($rows[0][0], true);
    $data['status'] = $rows[0][1];
    echo json_encode($data, JSON_FLAGS);
    echo "\n}\n";

    tucal_exit();
}

function courses() {
    global $USER;

    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        error(405);
    }

    $mnr = $_GET['mnr'] ?? null;
    if ($mnr === null) {
        error(501);
    }

    if (!isset($USER)) {
        error(401);
    } elseif ($USER['mnr'] !== $mnr) {
        error(403);
    }

    $stmt = db_exec("
            SELECT c.course_nr, c.semester, c.ects, cd.type, cd.name_de, cd.name_en,
                   ca.acronym_1, ca.acronym_2, ca.short, ca.program
            FROM tucal.v_account_group m
            LEFT JOIN tiss.course c ON (c.course_nr, c.semester) = (m.course_nr, m.semester)
            LEFT JOIN tiss.course_def cd ON cd.course_nr = c.course_nr
            LEFT JOIN tucal.course_acronym ca ON ca.course_nr = c.course_nr
            WHERE m.mnr = :mnr", [
        'mnr' => $mnr,
    ]);

    function echo_course($row) {
        $data = [
            'nr' => $row['course_nr'],
            'semester' => $row['semester'],
            'ects' => (float) $row['ects'],
            'type' => $row['type'],
            'name_de' => $row['name_de'],
            'name_en' => $row['name_en'],
            'acronym_1' => $row['acronym_1'],
            'acronym_2' => $row['acronym_2'],
            'short' => $row['short'],
            'program' => $row['program'],
        ];
        echo json_encode($data, JSON_FLAGS);
    }

    echo '{"status":"success","message":"work in progress","data":{"personal":[' . "\n";
    $first = true;
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        if ($first) {
            $first = false;
        } else {
            echo ",\n";
        }
        echo_course($row);
    }

    echo "\n],\"friends\":[\n";

    $stmt = db_exec("SELECT account_nr_1 FROM tucal.friend WHERE account_nr_2 = :nr", ['nr' => $USER['nr']]);
    $friends = [];
    while ($row = $stmt->fetch(PDO::FETCH_NUM)) {
        $friends[] = $row[0];
    }
    $friendsStr = '{' . implode(',', $friends) . '}';

    $stmt = db_exec("
            SELECT DISTINCT c.course_nr, c.semester, c.ects, cd.type, cd.name_de, cd.name_en,
                   ca.acronym_1, ca.acronym_2, ca.short, ca.program
            FROM tucal.v_account_group m
            LEFT JOIN tiss.course c ON (c.course_nr, c.semester) = (m.course_nr, m.semester)
            LEFT JOIN tiss.course_def cd ON cd.course_nr = c.course_nr
            LEFT JOIN tucal.course_acronym ca ON ca.course_nr = c.course_nr
            WHERE m.account_nr = ANY(:friends)", [
        'friends' => $friendsStr,
    ]);
    $first = true;
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        if ($first) {
            $first = false;
        } else {
            echo ",\n";
        }
        echo_course($row);
    }

    echo "\n]}}\n";
    tucal_exit();
}
