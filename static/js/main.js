document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // Common Helpers
    // ----------------------------------------------------
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const alertBox = document.getElementById('toast-alert');
        const msgSpan = document.getElementById('toast-message');
        
        if (!container || !alertBox || !msgSpan) return;
        
        msgSpan.textContent = message;
        alertBox.className = `alert alert-${type === 'error' ? 'danger' : type}`;
        container.style.display = 'block';
        container.style.opacity = '1';
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            container.style.opacity = '0';
            setTimeout(() => { container.style.display = 'none'; }, 300);
        }, 5000);
    }

    // Dismiss alert messages manually
    const closeButtons = document.querySelectorAll('.alert-close');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const alert = e.target.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            }
        });
    });

    // ----------------------------------------------------
    // Theme Switcher Logic
    // ----------------------------------------------------
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || 'dark';

    if (currentTheme === 'light') {
        document.body.classList.add('light-theme');
        if (themeToggle) themeToggle.textContent = '☀️';
    } else {
        if (themeToggle) themeToggle.textContent = '🌙';
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('light-theme');
            let theme = 'dark';
            if (document.body.classList.contains('light-theme')) {
                theme = 'light';
                themeToggle.textContent = '☀️';
            } else {
                themeToggle.textContent = '🌙';
            }
            localStorage.setItem('theme', theme);
        });
    }

    // ----------------------------------------------------
    // Dynamic Bulk controls logic builder helper
    // ----------------------------------------------------
    function initBulkControls(presentBtnId, absentBtnId) {
        const presentBtn = document.getElementById(presentBtnId);
        const absentBtn = document.getElementById(absentBtnId);

        if (presentBtn) {
            presentBtn.addEventListener('click', () => {
                document.querySelectorAll('.toggle-present').forEach(el => {
                    el.classList.add('active');
                    const absentSibling = el.nextElementSibling;
                    if (absentSibling) absentSibling.classList.remove('active');
                    
                    const studentId = el.dataset.studentId;
                    const hiddenInput = document.getElementById(`status-input-${studentId}`);
                    if (hiddenInput) hiddenInput.value = 'Present';
                });
            });
        }

        if (absentBtn) {
            absentBtn.addEventListener('click', () => {
                document.querySelectorAll('.toggle-absent').forEach(el => {
                    el.classList.add('active');
                    const presentSibling = el.previousElementSibling;
                    if (presentSibling) presentSibling.classList.remove('active');
                    
                    const studentId = el.dataset.studentId;
                    const hiddenInput = document.getElementById(`status-input-${studentId}`);
                    if (hiddenInput) hiddenInput.value = 'Absent';
                });
            });
        }
    }

    // Bind individual toggles dynamic click handlers
    function bindIndividualToggles() {
        document.querySelectorAll('.toggle-option').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                const option = e.target;
                const studentId = option.dataset.studentId;
                const hiddenInput = document.getElementById(`status-input-${studentId}`);
                
                if (!hiddenInput) return;

                if (option.classList.contains('toggle-present')) {
                    option.classList.add('active');
                    const absentSibling = option.nextElementSibling;
                    if (absentSibling) absentSibling.classList.remove('active');
                    hiddenInput.value = 'Present';
                } else if (option.classList.contains('toggle-absent')) {
                    option.classList.add('active');
                    const presentSibling = option.previousElementSibling;
                    if (presentSibling) presentSibling.classList.remove('active');
                    hiddenInput.value = 'Absent';
                }
            });
        });
    }

    // ----------------------------------------------------
    // 1. Mark Attendance SPA Logic
    // ----------------------------------------------------
    const markFilterForm = document.getElementById('attendance-filter-form');
    const markingContainer = document.getElementById('marking-sheet-container');
    
    if (markFilterForm) {
        markFilterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const date = document.getElementById('date').value;
            const class_name = document.getElementById('class_name').value;
            const section = document.getElementById('section').value;
            
            if (!date || !class_name || !section) return;

            // Hide previous tables/warnings
            markingContainer.style.display = 'none';
            document.getElementById('empty-class-warning').style.display = 'none';
            document.getElementById('duplicate-warning').style.display = 'none';
            document.getElementById('attendance-sheet-form').style.display = 'none';
            document.getElementById('report-sheet-container').style.display = 'none';

            // Query API
            fetch(`/api/students/?date=${date}&class_name=${class_name}&section=${section}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'error') {
                        showToast(data.message, 'error');
                        return;
                    }

                    markingContainer.style.display = 'block';
                    document.getElementById('sheet-title').textContent = `Attendance Sheet: Class ${class_name}-${section}`;
                    document.getElementById('sheet-date-text').textContent = date;

                    if (data.exists) {
                        // Show duplicate sheet warning
                        document.getElementById('duplicate-warning').style.display = 'block';
                        document.getElementById('bulk-controls').style.display = 'none';
                        
                        // Set up direct edit transition without reload
                        const editBtn = document.getElementById('go-to-edit-btn');
                        editBtn.onclick = () => {
                            window.location.href = `/attendance/report/?date=${date}&session_id=${data.session_id}`;
                        };
                    } else if (data.students.length === 0) {
                        // Empty Class Soft Warning
                        document.getElementById('empty-class-warning').style.display = 'block';
                        document.getElementById('bulk-controls').style.display = 'none';
                    } else {
                        // Build marking sheet rows
                        document.getElementById('bulk-controls').style.display = 'flex';
                        document.getElementById('attendance-sheet-form').style.display = 'block';
                        
                        const tbody = document.getElementById('student-rows');
                        tbody.innerHTML = ''; // clear

                        data.students.forEach(student => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td style="font-weight: 600;">${student.roll_number}</td>
                                <td style="font-weight: 500;">${student.name}</td>
                                <td style="text-align: right;">
                                    <input type="hidden" name="status_${student.id}" id="status-input-${student.id}" value="Present">
                                    <div class="status-toggle">
                                        <span class="toggle-option toggle-present active" data-student-id="${student.id}">Present</span>
                                        <span class="toggle-option toggle-absent" data-student-id="${student.id}">Absent</span>
                                    </div>
                                </td>
                            `;
                            tbody.appendChild(tr);
                        });

                        // Rebind listeners
                        bindIndividualToggles();
                        initBulkControls('mark-all-present', 'mark-all-absent');
                        
                        // Scroll down smoothly
                        markingContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                })
                .catch(err => showToast("Failed to fetch class sheet.", "error"));
        });

        // Intercept Attendance sheet saving via API
        const sheetForm = document.getElementById('attendance-sheet-form');
        sheetForm.addEventListener('submit', (e) => {
            e.preventDefault();

            const date = document.getElementById('date').value;
            const class_name = document.getElementById('class_name').value;
            const section = document.getElementById('section').value;

            // Collect entries statuses
            const entries = {};
            document.querySelectorAll('#student-rows tr').forEach(row => {
                const hiddenInput = row.querySelector('input[type="hidden"]');
                if (hiddenInput) {
                    const studentId = hiddenInput.id.replace('status-input-', '');
                    entries[studentId] = hiddenInput.value;
                }
            });

            // Post payload
            const payload = {
                date: date,
                class_name: class_name,
                section: section,
                entries: entries
            };

            fetch('/api/mark/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    markingContainer.style.display = 'none'; // hide sheet
                    
                    // Show report panel directly without page reload!
                    loadReportDetail(data.session_id, 'report-sheet-container');
                } else {
                    showToast(data.message, 'error');
                }
            })
            .catch(err => showToast("Failed to save attendance.", "error"));
        });
    }

    // ----------------------------------------------------
    // 2. Attendance Report SPA Logic
    // ----------------------------------------------------
    const reportSearchForm = document.getElementById('report-search-form');
    const sessionsPanel = document.getElementById('sessions-panel');
    const reportDisplay = document.getElementById('report-display-container');
    const editContainer = document.getElementById('editing-sheet-container');

    if (reportSearchForm) {
        // Auto-search sessions when date changes
        const dateInput = reportSearchForm.querySelector('input[type="date"]');
        if (dateInput) {
            dateInput.addEventListener('change', () => {
                const submitBtn = reportSearchForm.querySelector('button[type="submit"]');
                if (submitBtn) submitBtn.click();
            });
        }

        reportSearchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const date = reportSearchForm.querySelector('input[type="date"]').value;
            if (!date) return;

            // Hide previous displays
            sessionsPanel.style.display = 'none';
            reportDisplay.style.display = 'none';
            editContainer.style.display = 'none';

            fetch(`/api/sessions/?date=${date}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'error') {
                        showToast(data.message, 'error');
                        return;
                    }

                    sessionsPanel.style.display = 'block';
                    document.getElementById('sessions-date-text').textContent = date;
                    
                    const listContainer = document.getElementById('sessions-list');
                    listContainer.innerHTML = '';

                    if (data.sessions.length === 0) {
                        // Dynamic empty state CTA
                        listContainer.innerHTML = `
                            <div style="padding: 10px 0; display: flex; flex-direction: column; gap: 12px; align-items: flex-start; width: 100%;">
                                <p style="color: var(--text-secondary); font-size: 14px; margin: 0;">
                                    No attendance sheets marked for this date.
                                </p>
                                <button type="button" id="mark-now-btn" class="btn btn-accent" style="font-size: 13px;">
                                    📝 Mark Attendance for ${date}
                                </button>
                            </div>
                        `;
                        
                        document.getElementById('mark-now-btn').onclick = () => {
                            window.location.href = `/attendance/mark/?date=${date}`;
                        };
                    } else {
                        // Render session buttons
                        data.sessions.forEach(sess => {
                            const btn = document.createElement('button');
                            btn.className = 'btn btn-secondary';
                            btn.style.padding = '10px 16px';
                            btn.textContent = `Class ${sess.class_name}-${sess.section}`;
                            btn.addEventListener('click', () => {
                                // Toggle active class
                                listContainer.querySelectorAll('button').forEach(b => b.className = 'btn btn-secondary');
                                btn.className = 'btn btn-primary';
                                
                                editContainer.style.display = 'none'; // hide edits if open
                                loadReportDetail(sess.id, 'report-display-container');
                            });
                            listContainer.appendChild(btn);
                        });
                    }
                    
                    sessionsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                })
                .catch(err => showToast("Failed to fetch sessions.", "error"));
        });

        // Check query parameters to auto-load session report dynamically on mount
        const urlParams = new URLSearchParams(window.location.search);
        const urlDate = urlParams.get('date');
        const urlSessionId = urlParams.get('session_id');

        if (urlDate) {
            reportSearchForm.querySelector('input[type="date"]').value = urlDate;
            
            // Simulates clicking search first, then auto clicks session
            fetch(`/api/sessions/?date=${urlDate}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success' && data.sessions.length > 0) {
                        sessionsPanel.style.display = 'block';
                        document.getElementById('sessions-date-text').textContent = urlDate;
                        
                        const listContainer = document.getElementById('sessions-list');
                        listContainer.innerHTML = '';

                        data.sessions.forEach(sess => {
                            const btn = document.createElement('button');
                            btn.style.padding = '10px 16px';
                            
                            if (urlSessionId && sess.id == urlSessionId) {
                                btn.className = 'btn btn-primary';
                                loadReportDetail(sess.id, 'report-display-container');
                            } else {
                                btn.className = 'btn btn-secondary';
                            }
                            
                            btn.textContent = `Class ${sess.class_name}-${sess.section}`;
                            btn.addEventListener('click', () => {
                                listContainer.querySelectorAll('button').forEach(b => b.className = 'btn btn-secondary');
                                btn.className = 'btn btn-primary';
                                editContainer.style.display = 'none';
                                loadReportDetail(sess.id, 'report-display-container');
                            });
                            listContainer.appendChild(btn);
                        });
                    }
                });
        }
    }

    // Load and render report summary and table details dynamically
    function loadReportDetail(sessionId, containerId) {
        const container = document.getElementById(containerId);
        container.style.display = 'none';

        fetch(`/api/report/?session_id=${sessionId}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'error') {
                    showToast(data.message, 'error');
                    return;
                }

                const s = data.session;
                const sum = data.summary;

                container.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 24px; border-bottom: 1px solid var(--card-border); padding-bottom: 15px;">
                        <div>
                            <h2 style="font-size: 20px; font-weight: 700;">
                                Class ${s.class_name}-${s.section} Report
                            </h2>
                            <p style="color: var(--text-secondary); font-size: 14px; margin-top: 4px;">
                                Date: <strong>${s.date}</strong> | Marked by: <strong>${s.marked_by}</strong>
                            </p>
                        </div>
                        
                        <!-- Actions -->
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <a href="/attendance/${s.id}/export/" class="btn btn-secondary" style="font-size: 13px;">
                                📥 Export CSV
                            </a>
                            <button type="button" id="print-report-btn" class="btn btn-secondary" style="font-size: 13px;">
                                🖨️ Print Report
                            </button>
                            <button type="button" id="edit-report-btn" class="btn btn-accent" style="font-size: 13px;">
                                ✏️ Edit Attendance
                            </button>
                        </div>
                    </div>

                    <!-- Statistics Grid -->
                    <div class="metrics-grid" style="margin-bottom: 24px;">
                        <div class="glass-panel metric-card" style="min-height: 100px; padding: 16px;">
                            <div class="metric-label">Total Strength</div>
                            <div class="metric-value" style="font-size: 28px;">${sum.total}</div>
                        </div>
                        <div class="glass-panel metric-card present" style="min-height: 100px; padding: 16px;">
                            <div class="metric-label">Present</div>
                            <div class="metric-value" style="font-size: 28px; color: var(--present-color);">${sum.present}</div>
                        </div>
                        <div class="glass-panel metric-card absent" style="min-height: 100px; padding: 16px;">
                            <div class="metric-label">Absent</div>
                            <div class="metric-value" style="font-size: 28px; color: var(--absent-color);">${sum.absent}</div>
                        </div>
                    </div>

                    <!-- Table -->
                    <div class="table-container">
                        <table class="glass-table">
                            <thead>
                                <tr>
                                    <th style="width: 120px;">Roll Number</th>
                                    <th>Student Name</th>
                                    <th>Class</th>
                                    <th>Section</th>
                                    <th style="width: 150px; text-align: right;">Status</th>
                                </tr>
                            </thead>
                            <tbody id="report-rows">
                                <!-- Populated below -->
                            </tbody>
                        </table>
                    </div>
                `;

                const tbody = container.querySelector('#report-rows');
                data.entries.forEach(entry => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td style="font-weight: 600;">${entry.roll_number}</td>
                        <td style="font-weight: 500;">${entry.name}</td>
                        <td>Class ${entry.class_name}</td>
                        <td>${entry.section}</td>
                        <td style="text-align: right;">
                            <span class="badge ${entry.status === 'Present' ? 'badge-present' : 'badge-absent'}">
                                ${entry.status}
                            </span>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });

                container.style.display = 'block';
                
                // Bind Print handler
                container.querySelector('#print-report-btn').onclick = () => window.print();

                // Bind Dynamic Edit Panel transition handler
                container.querySelector('#edit-report-btn').onclick = () => {
                    loadEditSheet(s.id, data.entries);
                };

                container.scrollIntoView({ behavior: 'smooth', block: 'start' });
            })
            .catch(err => showToast("Failed to load report detail.", "error"));
    }

    // ----------------------------------------------------
    // 3. Edit Attendance SPA Logic
    // ----------------------------------------------------
    function loadEditSheet(sessionId, entries) {
        // Hide report display panel
        if (reportDisplay) reportDisplay.style.display = 'none';
        
        editContainer.style.display = 'block';
        editContainer.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 20px; border-bottom: 1px solid var(--card-border); padding-bottom: 15px;">
                <div>
                    <h1 class="panel-title" style="font-size: 20px; font-weight: 700;">
                        Correct Attendance Sheet
                    </h1>
                </div>
                
                <!-- Bulk Controls -->
                <div class="attendance-actions" id="edit-bulk-controls">
                    <button type="button" id="edit-mark-all-present" class="btn btn-secondary" style="font-size: 13px; font-weight: 500;">
                        ✓ All Present
                    </button>
                    <button type="button" id="edit-mark-all-absent" class="btn btn-secondary" style="font-size: 13px; font-weight: 500;">
                        ✗ All Absent
                    </button>
                </div>
            </div>

            <form id="attendance-edit-form">
                <div class="table-container">
                    <table class="glass-table">
                        <thead>
                            <tr>
                                <th style="width: 120px;">Roll Number</th>
                                <th>Student Name</th>
                                <th style="width: 250px; text-align: right;">Status Toggle</th>
                            </tr>
                        </thead>
                        <tbody id="edit-student-rows">
                            <!-- Populated below -->
                        </tbody>
                    </table>
                </div>
                
                <!-- Mandatory Reason for Modification -->
                <div class="glass-panel" style="padding: 20px; margin-top: 24px; background: rgba(15, 23, 42, 0.4); border: 1px solid var(--card-border);">
                    <div class="form-group" style="margin-bottom: 0;">
                        <label for="edit_reason" class="form-label" style="font-weight: 600; color: var(--text-primary);">
                            Reason for Modification <span style="color: var(--absent-color);">*</span>
                        </label>
                        <textarea name="edit_reason" id="edit_reason" class="form-input" style="width: 100%; min-height: 80px; resize: vertical;" required placeholder="Please explain why these attendance records are being corrected (e.g., student arrived late, entry error)..."></textarea>
                    </div>
                </div>
                
                <div class="form-actions">
                    <button type="button" id="cancel-edit-btn" class="btn btn-secondary">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Modifications</button>
                </div>
            </form>
        `;

        const tbody = document.getElementById('edit-student-rows');
        entries.forEach(entry => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 600;">${entry.roll_number}</td>
                <td style="font-weight: 500;">${entry.name}</td>
                <td style="text-align: right;">
                    <input type="hidden" name="status_${entry.student_id}" id="status-input-${entry.student_id}" value="${entry.status}">
                    <div class="status-toggle">
                        <span class="toggle-option toggle-present ${entry.status === 'Present' ? 'active' : ''}" data-student-id="${entry.student_id}">
                            Present
                        </span>
                        <span class="toggle-option toggle-absent ${entry.status === 'Absent' ? 'active' : ''}" data-student-id="${entry.student_id}">
                            Absent
                        </span>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Bind helpers
        bindIndividualToggles();
        initBulkControls('edit-mark-all-present', 'edit-mark-all-absent');

        // Cancel handler
        document.getElementById('cancel-edit-btn').onclick = () => {
            editContainer.style.display = 'none';
            if (reportDisplay) reportDisplay.style.display = 'block';
        };

        // Form submit handler
        const editForm = document.getElementById('attendance-edit-form');
        editForm.addEventListener('submit', (e) => {
            e.preventDefault();

            const reason = document.getElementById('edit_reason').value.strip();
            if (!reason) {
                showToast("Reason for modification is mandatory.", "error");
                return;
            }

            // Collect updated statuses
            const updatedEntries = {};
            document.querySelectorAll('#edit-student-rows tr').forEach(row => {
                const hiddenInput = row.querySelector('input[type="hidden"]');
                if (hiddenInput) {
                    const studentId = hiddenInput.id.replace('status-input-', '');
                    updatedEntries[studentId] = hiddenInput.value;
                }
            });

            const payload = {
                session_id: sessionId,
                entries: updatedEntries,
                edit_reason: reason
            };

            fetch('/api/edit/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    editContainer.style.display = 'none';
                    
                    // Reload report panel dynamically
                    loadReportDetail(sessionId, 'report-display-container');
                } else {
                    showToast(data.message, 'error');
                }
            })
            .catch(err => showToast("Failed to correct attendance.", "error"));
        });

        editContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // 5. Mobile Menu Toggle Logic
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const sidebarNav = document.getElementById('sidebar-nav');
    
    if (mobileMenuToggle && sidebarNav) {
        mobileMenuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebarNav.classList.toggle('open');
        });

        // Click outside to close sidebar on mobile
        document.addEventListener('click', (e) => {
            if (sidebarNav.classList.contains('open') && !sidebarNav.contains(e.target) && e.target !== mobileMenuToggle) {
                sidebarNav.classList.remove('open');
            }
        });
    }

    // Utility Polyfill for string stripping
    if (!String.prototype.strip) {
        String.prototype.strip = function() {
            return this.replace(/^\s+|\s+$/g, '');
        };
    }
});
