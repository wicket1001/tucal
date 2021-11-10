
INSERT INTO tiss.course_type (type, name_de, name_en)
VALUES ('VO', 'Vorlesung', 'Lecture'),
       ('VU', 'Vorlesung mit Übung', 'Lecture and Exercise'),
       ('UE', 'Übung', 'Exercise'),
       ('AE', 'Arbeitsgemeinschaft und Exkursion', 'Working Group and Excursion'),
       ('AG', 'Arbeitsgemeinschaft', 'Working Group'),
       ('AU', 'Angeleitete Übung', 'Guided Exercise'),
       ('EP', 'Studieneingangsphase', 'Studieneingangsphase'),
       ('EU', 'Entwurfsübung', 'Design Lab'),
       ('EX', 'Exkursion', 'Excursion'),
       ('FU', 'Feldübung', 'Field Exercise'),
       ('IP', 'Interdisziplinäre Projekte', 'Interdisciplinary Projects'),
       ('KO', 'Konversatorium', 'Conversatorium'),
       ('KU', 'Konstruktionsübung', 'Construction Exercise'),
       ('KV', 'Konversatorium', 'Conversatorium'),
       ('LU', 'Laborübung', 'Laboratory Exercise'),
       ('MU', 'Messübung', 'Measure Exercise'),
       ('PA', 'Projektarbeit', 'Project'),
       ('PN', 'Präsentation', 'Presentation'),
       ('PR', 'Projekt', 'Project'),
       ('PS', 'Proseminar', 'Introductory Seminar'),
       ('PU', 'Praktische Übung', 'Practical Exercise'),
       ('PV', 'Privatissimum', 'Research Seminar'),
       ('RE', 'Repetitorium', 'Revision Course'),
       ('RU', 'Rechenübung', 'Calc. Exercise'),
       ('RV', 'Ringvorlesung', 'Lecture Series'),
       ('SE', 'Seminar', 'Seminar'),
       ('SP', 'Seminar mit Praktikum', 'Seminar adn Practice'),
       ('SV', 'Spezialvorlesung', 'Special Lecture'),
       ('UX', 'Übung und Exkursion', 'Exercise and Excursion'),
       ('VD', 'Vorlesung mit Demonstration', 'Lecture and Demonstration'),
       ('VL', 'Vorlesung mit Laborübung', 'Lecture and Laboratory Exercise'),
       ('VR', 'Vorlesung und Rechenübung', 'Lecture and Calc. Exercise'),
       ('VX', 'Vorlesung und Exkursion', 'Lecture and Excursion'),
       ('ZU', 'Zeichenübung', 'Drawing Exercise');

INSERT INTO tiss.event_type (type, name_de, name_en)
VALUES (0, 'Allgemeine Reservierung', 'General reservation'),
       (1, 'Lehrveranstaltung', 'Course'),
       (2, 'Gruppentermin', 'Group date'),
       (3, 'Prüfungstermin', 'Examination date'),
       (4, 'Institute und Organisationen', 'Institutes and organisations');
