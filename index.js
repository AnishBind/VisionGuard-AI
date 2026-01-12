const express = require('express');
const mysql = require('mysql2');
const bodyParser = require('body-parser');
const session = require('express-session');

const app = express();
const port = 4000;

app.set('view engine', 'ejs');
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());
app.use(session({
    secret: '1234',
    resave: false,
    saveUninitialized: true,
    cookie: { secure: false }
}));

var con = mysql.createConnection({
  host: "localhost",
  user: "root",
  password: "admin",
  database: "hospital"
});

con.connect(function(err) {
  if (err) {
    console.log(err)
  }else{
  console.log("Connected!");
  }
  con.query("SELECT * FROM ambulance", function (err, result, fields) {
    if (err) {
        console.log(err);
    }
  });
});

app.get('/', (req, res) => {
    res.render('index'); 
  });




app.get('/login', (req, res) => {
    res.render('login', { user: req.session.user }); 
  });
  
  app.post('/login', (req, res) => {
    const { email, password } = req.body;
    con.query('SELECT * FROM users WHERE email = ?', [email], async (err, results) => {
      if (err) {
        console.error('Error querying database:', err.stack);
        res.json({ success: false, message: 'Error processing your request.' });
        return;
      }
  
      if (results.length === 0) {
        res.json({ success: false, message: 'Invalid email or password.' });
        return;
      }
  
      const user = results[0];
  
      
      if (password===user.password) {
        req.session.user = { user: user };
        if(user.role=='patient'){
            res.json({ success: true, redirect: '/patient' }); 
        }
        else if(user.role=='doctor'){
            res.json({ success: true, redirect: '/doctor'}); 
            
        }
        else if(user.role=='ngo'){
            res.json({ success: true, redirect: '/ngo'}); 
        }
      } else {
        
        res.json({ success: false, message: 'Invalid email or password.' });
      }
    });
  });

app.post('/logout', (req, res) => {
    req.session.destroy((err) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ success: false, message: 'Error logging out' });
        }
        res.json({ success: true });
    });
});

app.get('/signup', (req, res) => {
    res.render('signup'); 
  });

 
app.post('/signup', async (req, res) => {
    const { name, email, password, role, dob, phone, specialization, experience, hours, ngoDescription } = req.body;


    const insertQuery = `
    INSERT INTO users (name, email, password, role, dob, phone, specialization, experience, hours, ngo_description)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;
    const values = [name, email, password, role, dob, phone, specialization || null, experience || null, hours || null, ngoDescription || null];

    con.query(insertQuery, values, (error, results) => {
    if (error) {
        console.error('Error inserting data:', error.stack);
        return res.json({ success: false, message: 'Error saving data to the database.' });
    }

    res.json({ success: true });
    });
});


app.get('/patient', (req, res) => {
    // Execute both queries simultaneously
    if(req.session.user.user.role!='patient'){
        res.send(req.session.user.user.role + "Can't open patient page")    
    }
    Promise.all([
        new Promise((resolve, reject) => {
            con.query('SELECT * FROM ambulance ORDER BY distance ASC', (error, results, fields) => {
                if (error) {
                    return reject(error);
                }
                resolve(results);
            });
        }),
        new Promise((resolve, reject) => {
            con.query("SELECT * FROM users WHERE role = 'doctor'", (error, results, fields) => {
                if (error) {
                    return reject(error);
                }
                resolve(results);
            });
        }),
        new Promise((resolve, reject) => {
            con.query("SELECT * FROM users WHERE role = 'ngo'", (error, results, fields) => {
                if (error) {
                    return reject(error);
                }
                resolve(results);
            });
        }),
    ])
    .then(([ambulanceResults, doctorResults,ngoResults]) => {
        // Render the page with both sets of results
        if (!req.session.user) {
            return res.redirect('/login');
        }
        res.render('patient', { data: ambulanceResults, doctor: doctorResults, ngo: ngoResults, user: req.session.user });
    })
    .catch(error => {
        console.log(error);
        res.status(500).send('Database query error');
    });
});

app.post('/book-appointment', (req, res) => {
    const { name, email, reason, time, doctorEmail } = req.body;

    const query = `
        INSERT INTO doctor (name, email, your_reason_of_consultation, select_appointment_time, doctor_email, appointment)
        VALUES (?, ?, ?, ?, ?, ?)
    `;
    
    con.query(query, [name, email, reason, time, doctorEmail, 'pending'], (error, results) => {
        if (error) {
            console.log(error);
            res.status(500).json({ success: false });
        } else {
            res.json({ success: true });
        }
    });
});

app.post('/add-member', (req, res) => {
    const { name, email, phone, quary,ngoEmail} = req.body;

    const sql = 'INSERT INTO member (name, email, phone, special_notes,ngoemail) VALUES (?, ?, ?, ?,?)';
    con.query(sql, [name, email, phone, quary,ngoEmail], (error, results) => {
        if (error) {
            console.log(error);
            return res.status(500).json({ success: false, message: 'Database query error' });
        }
        res.json({ success: true });
    });
});

app.post('/add-help', (req, res) => {
    const { name, email, phone, description, ngoEmail} = req.body;

    const sql = 'INSERT INTO help (name, email, phone, description,ngoemail) VALUES (?, ?, ?, ?,?)';
    con.query(sql, [name, email, phone, description,ngoEmail], (error, results) => {
        if (error) {
            console.log(error);
            return res.status(500).json({ success: false, message: 'Database query error' });
        }
        res.json({ success: true });
    });
});

app.post('/add-donation', (req, res) => {
    const { name, email, amount, purpose, upi_id, ngoemail } = req.body;

    const sql = 'INSERT INTO donations (name, email, amount, purpose, upi_id, ngoemail) VALUES (?, ?, ?, ?, ?, ?)';
    con.query(sql, [name, email, amount, purpose, upi_id, ngoemail], (error, results) => {
        if (error) {
            console.log(error);
            return res.status(500).json({ success: false, message: 'Database query error' });
        }
        res.json({ success: true });
    });
});


app.post('/add-report', (req, res) => {
    const { name, email, phone, incident_details, resolution } = req.body;

    // SQL query to insert data into the `report` table
    const query = 'INSERT INTO report (name, email, phone_number, incident_details, resolution) VALUES (?, ?, ?, ?, ?)';

    // Execute the query with the provided data
    con.query(query, [name, email, phone, incident_details, resolution], (error, results) => {
        if (error) {
            console.error('Error inserting report:', error);
            res.status(500).json({ success: false, message: 'Database query error' });
        } else {
            res.status(200).json({ success: true });
        }
    });
});

app.get('/doctor', (req, res) => {
    if (!req.session.user) {
        return res.redirect('/login');
    }
    else if(req.session.user.user.role!='doctor'){
        res.send(req.session.user.user.role + "Can't open doctor page")    
    }
    else{
        
    Promise.all([
        new Promise((resolve, reject) => {
            con.query('SELECT * FROM doctor', (error, results) => {
                if (error) {
                    reject(error);
                } else {
                    resolve(results);
                }
            });
        }),
        new Promise((resolve, reject) => {
            const email = req.session.user.user.email; 
            const query = 'SELECT * FROM doctor WHERE appointment = "Pending" AND doctor_email = ?';
            
            con.query(query, [email], (error, results) => {
                if (error) {
                    reject(error);
                } else {
                    resolve(results);
                }
            });
        }),
        
        new Promise((resolve, reject) => {
            const email = req.session.user.user.email; 
            const query = 'SELECT * FROM doctor WHERE appointment = "Accepted" AND doctor_email = ?';
            con.query(query, [email], (error, results) =>  {
                if (error) {
                    reject(error);
                } else {
                    resolve(results);
                }
            });
        }),
        new Promise((resolve, reject) => {
            con.query("SELECT * FROM users WHERE role = 'ngo'", (error, results, fields) => {
                if (error) {
                    return reject(error);
                }
                resolve(results);
            });
        })
    ])
    .then(([allDoctors, pendingAppointments, acceptedConsultations, ngoResults]) => {
        // Render the view with all sets of data
        res.render('doctor', {
            patients: allDoctors,
            appointments: pendingAppointments,
            consultations: acceptedConsultations,
            ngo: ngoResults,
            user: req.session.user
        });
    })
    .catch((error) => {
        console.log(error);
        res.status(500).send('Database query error');
    });
}
});

app.get('/ngo-members/:ngoemail', (req, res) => {
    const ngoemail = req.params.ngoemail;

    const query = 'SELECT * FROM ngoMembers WHERE ngoemail = ?';

    con.query(query, [ngoemail], (err, results) => {
        if (err) {
            console.error('Database query error:', err);
            res.status(500).send('Database query error');
        } else {
            res.json({ members: results });
        }
    });
});



app.post('/appointments/accept/:id', (req, res) => {
    const appointmentId = req.params.id;
    con.query('UPDATE doctor SET appointment = "Accepted" WHERE id = ?', [appointmentId], (error) => {
        if (error) {
            console.log(error);
            res.status(500).send('Database update error');
        } else {
            res.redirect('/doctor');
        }
    });
});

app.post('/appointments/reject/:id', (req, res) => {
    const appointmentId = req.params.id;
    con.query('DELETE FROM doctor WHERE id = ?', [appointmentId], (error) => {
        if (error) {
            console.log(error);
            res.status(500).send('Database delete error');
        } else {
            res.redirect('/doctor');
        }
    });
});


app.get('/ngo', (req, res) => {
    if (!req.session.user) {
        return res.redirect('/login');
    }
    else if(req.session.user.user.role!='ngo'){
        res.send(req.session.user.user.role + "Can't open ngo page")    
    }
    else{
    Promise.all([
        new Promise((resolve, reject) => {
            const ngoemail = req.session.user.user.email; // Extract ngoemail from session
        
            const query = 'SELECT * FROM member WHERE ngoemail = ?';
        
            con.query(query, [ngoemail], (err, results) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(results);
                }
            });
        }),
        
        new Promise((resolve, reject) => {
            const ngoemail = req.session.user.user.email; // Extract ngoemail from session
        
            const query = 'SELECT * FROM donations WHERE ngoemail = ?';
        
            con.query(query, [ngoemail], (err, results) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(results);
                }
            });
        }),

        new Promise((resolve, reject) => {
            const ngoemail = req.session.user.user.email; // Extract ngoemail from session
        
            const query = 'SELECT * FROM help WHERE ngoemail = ?';
        
            con.query(query, [ngoemail], (err, results) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(results);
                }
            });
        }),

        new Promise((resolve, reject) => {
            const query = 'SELECT * FROM report';
            con.query(query, (err, results) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(results);
                }
            });
        }),

        
    ])
    .then(([members, donations, helpRequests, reports]) => {
        
        res.render('ngo', { members, donations, helpRequests, reports, user: req.session.user});
    })
    .catch((error) => {
        console.log(error);
        res.status(500).send('Database query error');
    });
}
});



app.post('/acceptMember', (req, res) => {
    const memberId = req.body.memberId;

    // Query to get the member data
    const getMemberQuery = 'SELECT * FROM member WHERE email = ?';
    con.query(getMemberQuery, [memberId], (err, results) => {
        if (err) {
            console.log(err);
            return res.status(500).send('Database query error');
        }

        if (results.length === 0) {
            return res.status(404).send('Member not found');
        }

        const member = results[0];

        // Query to insert the member into ngoMembers
        const insertMemberQuery = 'INSERT INTO ngoMembers (name, email,phone, ngoemail) VALUES (?, ?,?,?)';
    con.query(insertMemberQuery, [member.name, member.email,member.phone,member.ngoemail], (insertErr) => {
            if (insertErr) {
                console.log(insertErr);
                return res.status(500).send('Database query error');
            }

            // Query to delete the member from the member table
            const deleteMemberQuery = 'DELETE FROM member WHERE email = ?';
            con.query(deleteMemberQuery, [memberId], (deleteErr) => {
                if (deleteErr) {
                    console.log(deleteErr);
                    return res.status(500).send('Database query error');
                }

                res.redirect('/ngo');
            });
        });
    });
});


app.post('/rejectMember', (req, res) => {
    const memberId = req.body.memberId;

    // Query to delete the member from the member table
    const deleteMemberQuery = 'DELETE FROM member WHERE id = ?';
    con.query(deleteMemberQuery, [memberId], (err) => {
        if (err) {
            console.log(err);
            return res.status(500).send('Database query error');
        }

        res.redirect('/ngo');
    });
});


app.post('/acceptHelp', (req, res) => {
    const helpId = req.body.helpId;

    // Query to get the help request data
    const getHelpQuery = 'SELECT * FROM help WHERE id = ?';
    con.query(getHelpQuery, [helpId], (err, results) => {
        if (err) {
            console.log(err);
            return res.status(500).send('Database query error');
        }

        if (results.length === 0) {
            return res.status(404).send('Help request not found');
        }

        // Query to delete the help request from the help table
        const deleteHelpQuery = 'DELETE FROM help WHERE id = ?';
        con.query(deleteHelpQuery, [helpId], (deleteErr) => {
            if (deleteErr) {
                console.log(deleteErr);
                return res.status(500).send('Database query error');
            }

            res.redirect('/ngo');
            });
        });
    });




app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
  });