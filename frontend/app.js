const formSchema = {
    product: ['title', 'description', 'price', 'category', 'main_image'],
    article: ['title', 'description', 'author', 'publish_date'],
    profile: ['name', 'bio', 'profile_image']
};

// URL Fetch Handler
document.getElementById('fetchBtn').addEventListener('click', async () => {
    const url = document.getElementById('urlInput').value;
    if (!url) return alert('Please enter a URL');

    const fetchBtn = document.getElementById('fetchBtn');
    const originalText = fetchBtn.innerText;
    fetchBtn.disabled = true;
    fetchBtn.innerHTML = 'Fetching... <span class="spinner"></span>';

    try {
        const response = await fetch('http://localhost:3000/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        generateForm(data);
    } catch (error) {
        alert('Error fetching URL: ' + error.message);
    } finally {
        fetchBtn.disabled = false;
        fetchBtn.innerText = originalText;
    }
});

// File Upload Elements
const fileInput = document.getElementById('fileInput');
const uploadContainer = document.getElementById('uploadContainer');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const uploadBtn = document.getElementById('uploadBtn');
const showExtractorBtn = document.getElementById('showExtractorBtn');
let selectedFile = null;

function setExtractorVisibility(show) {
    const urlSection = document.getElementById('urlSection');
    const fileSection = document.getElementById('fileSection');
    const extractorDivider = document.getElementById('extractorDivider');
    const btn = document.getElementById('showExtractorBtn');

    if (urlSection) urlSection.style.display = show ? '' : 'none';
    if (fileSection) fileSection.style.display = show ? '' : 'none';
    if (extractorDivider) extractorDivider.style.display = show ? '' : 'none';
    if (btn) btn.style.display = show ? 'none' : 'inline-flex';
}

if (showExtractorBtn) {
    showExtractorBtn.addEventListener('click', () => {
        setExtractorVisibility(true);
    });
}

// Click to upload
uploadContainer.addEventListener('click', () => {
    fileInput.click();
});

// File input change
fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
});

// Drag and drop handlers
uploadContainer.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadContainer.classList.add('dragover');
});

uploadContainer.addEventListener('dragleave', () => {
    uploadContainer.classList.remove('dragover');
});

uploadContainer.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadContainer.classList.remove('dragover');

    const file = e.dataTransfer.files[0];
    if (file) {
        handleFileSelect(file);
        fileInput.files = e.dataTransfer.files;
    }
});

// Handle file selection
function handleFileSelect(file) {
    if (!file) return;

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.style.display = 'block';
    uploadBtn.style.display = 'inline-block';
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Upload button handler
uploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    uploadBtn.disabled = true;
    const originalText = uploadBtn.innerText;
    uploadBtn.innerHTML = 'Processing... <span class="spinner"></span>';

    try {
        const response = await fetch('http://localhost:3000/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        generateForm(data);

        // Reset file selection
        selectedFile = null;
        fileInput.value = '';
        fileInfo.style.display = 'none';
        uploadBtn.style.display = 'none';
    } catch (error) {
        alert('Error processing file: ' + error.message);
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerText = originalText;
    }
});

let currentExtractedData = null; // Store current extracted data for saving
let isSavingProject = false;
let hasSavedCurrentExtraction = false;
let currentProjectId = null; // When set, save/update actions should target an existing project row

function generateForm(data, options = {}) {
    const container = document.getElementById('formContainer');
    container.innerHTML = ''; // clear previous
    currentExtractedData = data; // Store for saving
    const resolvedProjectId = Number.isInteger(options.projectId)
        ? options.projectId
        : (Number.isInteger(data?.id) ? data.id : null);
    currentProjectId = resolvedProjectId;
    hasSavedCurrentExtraction = false; // New extracted/viewed payload, allow one save/update

    if (!data || Object.keys(data).length === 0) {
        setExtractorVisibility(true);
        container.innerHTML = '<p style="color: #999;">No data extracted.</p>';
        return;
    }

    // Handle error cases
    if (data.error) {
        setExtractorVisibility(true);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'section';
        errorDiv.style.borderColor = 'var(--error)';
        errorDiv.style.color = 'var(--error)';
        errorDiv.innerHTML = `<strong>Error:</strong> ${data.message || data.error}`;
        container.appendChild(errorDiv);
        return;
    }

    // Hide extractor sections when showing extracted/result data
    setExtractorVisibility(false);

    // For project schema data, render fully nested labeled form fields
    if (isProjectSchemaData(data)) {
        renderProjectSchemaForm(container, data);

        // Action buttons container
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'projects-toolbar';
        buttonContainer.style.marginTop = '2rem';

        const submitBtn = document.createElement('button');
        submitBtn.innerText = 'Submit';
        submitBtn.className = 'btn-primary';
        submitBtn.style.flex = '1';
        submitBtn.onclick = () => {
            const formData = getLiveFormData(container, currentExtractedData);
            console.log('Form Data:', formData);
            alert('Form submitted! Check console for data.');
        };
        buttonContainer.appendChild(submitBtn);

        const saveProjectBtn = document.createElement('button');
        saveProjectBtn.innerText = currentProjectId ? 'Update Project' : 'Save as Project';
        saveProjectBtn.className = 'btn-secondary';
        saveProjectBtn.style.flex = '1';
        saveProjectBtn.onclick = () => {
            const liveData = getLiveFormData(container, currentExtractedData);
            if (currentProjectId) {
                updateExistingProject(currentProjectId, liveData);
                return;
            }
            saveAsProject(liveData);
        };
        buttonContainer.appendChild(saveProjectBtn);

        container.appendChild(buttonContainer);
        return;
    }

    // Special handling for image data - display image preview first
    if (data.type === 'image' && data.imageUrl) {
        const imageSection = document.createElement('div');
        imageSection.className = 'section';

        const imageTitle = document.createElement('h3');
        imageTitle.textContent = 'Image Preview';
        imageTitle.className = 'field-label';
        imageSection.appendChild(imageTitle);

        const img = document.createElement('img');
        img.src = `http://localhost:3000${data.imageUrl}`;
        img.className = 'image-preview';
        img.style.maxWidth = '100%';
        img.style.borderRadius = 'var(--radius-md)';
        img.style.boxShadow = 'var(--shadow-md)';
        img.alt = data.filename || 'Uploaded image';
        imageSection.appendChild(img);

        // Image type and format info
        if (data.imageType || data.format) {
            const typeInfo = document.createElement('div');
            typeInfo.style.marginTop = '1rem';
            typeInfo.style.fontSize = '0.875rem';
            typeInfo.style.color = 'var(--text-muted)';
            typeInfo.innerHTML = `
                <strong>Image Type:</strong> ${data.imageType || 'Unknown'} | 
                <strong>Format:</strong> ${data.format || 'Unknown'} |
                <strong>MIME Type:</strong> ${data.mimeType || 'Unknown'}
            `;
            imageSection.appendChild(typeInfo);
        }

        // Dimensions info
        if (data.dimensions) {
            const dimInfo = document.createElement('div');
            dimInfo.style.marginTop = '10px';
            dimInfo.style.fontSize = '14px';
            dimInfo.style.color = '#666';
            dimInfo.innerHTML = `
                <strong>Dimensions:</strong> ${data.dimensions.width} × ${data.dimensions.height} pixels 
                (Aspect Ratio: ${data.dimensions.aspectRatio})
            `;
            imageSection.appendChild(dimInfo);
        }

        // OCR Error Message
        if (data.ocrError) {
            const ocrErrorDiv = document.createElement('div');
            ocrErrorDiv.style.marginTop = '1rem';
            ocrErrorDiv.style.padding = '1rem';
            ocrErrorDiv.style.backgroundColor = 'rgba(239, 68, 68, 0.05)';
            ocrErrorDiv.style.borderRadius = 'var(--radius-md)';
            ocrErrorDiv.style.borderLeft = '4px solid var(--error)';
            ocrErrorDiv.style.fontSize = '0.875rem';
            ocrErrorDiv.style.color = 'var(--error)';
            ocrErrorDiv.innerHTML = `
                <strong>⚠ OCR Warning:</strong> ${data.ocrError}
                ${data.warning ? `<br><span style="font-size: 11px; margin-top: 5px; display: block;">${data.warning}</span>` : ''}
            `;
            imageSection.appendChild(ocrErrorDiv);
        }

        // OCR Statistics (only show if OCR was successful)
        if (!data.ocrError && (data.hasText !== undefined || data.ocrConfidence || data.ocrWordCount)) {
            const ocrStats = document.createElement('div');
            ocrStats.style.marginTop = '15px';
            ocrStats.style.padding = '12px';
            ocrStats.style.backgroundColor = data.hasText ? '#e8f5e9' : '#fff3e0';
            ocrStats.style.borderRadius = '4px';
            ocrStats.style.fontSize = '14px';

            let statsText = '<strong>OCR Results:</strong> ';
            if (data.hasText) {
                statsText += '✓ Text detected | ';
            } else {
                statsText += '✗ No text detected | ';
            }
            if (data.ocrConfidence && data.ocrConfidence !== 'N/A') {
                statsText += `Confidence: ${data.ocrConfidence} | `;
            }
            if (data.ocrWordCount !== undefined) {
                statsText += `Words: ${data.ocrWordCount}`;
            }

            ocrStats.innerHTML = statsText;
            imageSection.appendChild(ocrStats);
        }

        container.appendChild(imageSection);
    }

    // Display parsed form data as JSON
    if (data.parsedFormData) {
        const jsonSection = document.createElement('div');
        jsonSection.className = 'section';

        const jsonTitle = document.createElement('h2');
        jsonTitle.textContent = 'Parser Result (JSON)';
        jsonTitle.className = 'field-label';
        jsonSection.appendChild(jsonTitle);

        // Create JSON textarea
        const jsonTextarea = document.createElement('pre');
        jsonTextarea.className = 'result-code';
        jsonTextarea.textContent = JSON.stringify(data.parsedFormData, null, 2);

        jsonSection.appendChild(jsonTextarea);
        container.appendChild(jsonSection);
    }

    // Generate dynamic form from CSV data with type-specific inputs
    if (data.type === 'csv' && data.headers && data.columnTypes && data.firstRowData) {
        const csvFormSection = document.createElement('div');
        csvFormSection.className = 'section';
        csvFormSection.style.borderLeft = '4px solid var(--success)';

        const formTitle = document.createElement('h2');
        formTitle.textContent = 'Dynamic Form (CSV)';
        formTitle.className = 'field-label';
        csvFormSection.appendChild(formTitle);

        const infoNote = document.createElement('div');
        infoNote.style.marginBottom = '1.5rem';
        infoNote.style.fontSize = '0.875rem';
        infoNote.style.color = 'var(--text-muted)';
        infoNote.innerHTML = `✓ Form generated with ${data.headers.length} fields. Pre-filled with first row data.`;
        csvFormSection.appendChild(infoNote);

        // Generate form fields for each column
        data.headers.forEach((header, index) => {
            const columnType = data.columnTypes[header] || { type: 'text', unit: null, currency: null };
            const fieldValue = data.firstRowData[header] || '';

            const fieldContainer = document.createElement('div');
            fieldContainer.className = 'data-field';

            const label = document.createElement('label');
            label.className = 'field-label';
            label.textContent = header;

            // Add type indicator
            const typeBadge = document.createElement('span');
            typeBadge.textContent = columnType.type;
            typeBadge.style.marginLeft = '0.5rem';
            typeBadge.style.padding = '2px 6px';
            typeBadge.style.backgroundColor = 'var(--bg)';
            typeBadge.style.color = 'var(--text-muted)';
            typeBadge.style.borderRadius = '4px';
            typeBadge.style.fontSize = '10px';
            typeBadge.style.textTransform = 'uppercase';
            label.appendChild(typeBadge);

            let input;

            // Create input based on detected type
            switch (columnType.type) {
                case 'email':
                    input = document.createElement('input');
                    input.type = 'email';
                    input.value = fieldValue;
                    break;
                case 'tel':
                    input = document.createElement('input');
                    input.type = 'tel';
                    input.value = fieldValue;
                    break;
                case 'date':
                    input = document.createElement('input');
                    input.type = 'date';
                    // Try to parse and format date
                    if (fieldValue) {
                        // Remove quotes if present
                        let cleanValue = fieldValue.toString().replace(/^"|"$/g, '').trim();

                        // Try different date formats
                        let dateMatch = cleanValue.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})/);
                        if (!dateMatch) {
                            // Try YYYY-MM-DD format
                            dateMatch = cleanValue.match(/(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})/);
                            if (dateMatch) {
                                // Already in YYYY-MM-DD format
                                input.value = `${dateMatch[1]}-${dateMatch[2].padStart(2, '0')}-${dateMatch[3].padStart(2, '0')}`;
                            } else {
                                // Try to parse as ISO date
                                const date = new Date(cleanValue);
                                if (!isNaN(date.getTime())) {
                                    input.value = date.toISOString().split('T')[0];
                                } else {
                                    input.value = '';
                                }
                            }
                        } else {
                            // MM/DD/YYYY or DD/MM/YYYY format
                            let year = dateMatch[3];
                            if (year.length === 2) year = '20' + year;

                            // Try MM/DD/YYYY first (US format)
                            let month = dateMatch[1].padStart(2, '0');
                            let day = dateMatch[2].padStart(2, '0');
                            let date = new Date(`${year}-${month}-${day}`);

                            // If invalid, try DD/MM/YYYY (international format)
                            if (isNaN(date.getTime()) || date.getDate() != parseInt(dateMatch[1])) {
                                month = dateMatch[2].padStart(2, '0');
                                day = dateMatch[1].padStart(2, '0');
                                date = new Date(`${year}-${month}-${day}`);
                            }

                            if (!isNaN(date.getTime())) {
                                input.value = date.toISOString().split('T')[0];
                            } else {
                                input.value = '';
                            }
                        }
                    }
                    break;
                case 'url':
                    input = document.createElement('input');
                    input.type = 'url';
                    input.value = fieldValue;
                    break;
                case 'number':
                    input = document.createElement('input');
                    input.type = 'number';
                    // Extract number from value (remove currency symbols, etc.)
                    const numMatch = fieldValue.toString().match(/-?\d+\.?\d*/);
                    input.value = numMatch ? numMatch[0] : fieldValue;
                    input.step = columnType.unit === '%' ? '0.01' : '0.01';
                    if (columnType.currency) {
                        input.style.paddingRight = '60px';
                    }
                    if (columnType.unit) {
                        label.innerHTML = `${header} (${columnType.unit})`;
                    }
                    break;
                case 'checkbox':
                    input = document.createElement('input');
                    input.type = 'checkbox';
                    input.checked = /^(true|yes|1)$/i.test(fieldValue);
                    break;
                default:
                    input = document.createElement('input');
                    input.type = 'text';
                    input.value = fieldValue;
            }

            // Common input styling
            input.name = `csv_${header}`;
            input.id = `csv_field_${index}`;
            input.style.width = '100%';
            input.style.maxWidth = '600px';
            input.style.padding = '12px';
            input.style.border = '2px solid #ddd';
            input.style.borderRadius = '6px';
            input.style.fontSize = '14px';
            input.style.transition = 'border-color 0.3s';

            input.addEventListener('focus', () => {
                input.style.borderColor = '#4CAF50';
                input.style.outline = 'none';
            });

            input.addEventListener('blur', () => {
                input.style.borderColor = '#ddd';
            });

            // Add currency or unit indicator if present
            if (columnType.currency && columnType.type === 'number') {
                const currencyWrapper = document.createElement('div');
                currencyWrapper.style.position = 'relative';
                currencyWrapper.style.display = 'inline-block';
                currencyWrapper.style.width = '100%';
                currencyWrapper.style.maxWidth = '600px';

                const currencyLabel = document.createElement('span');
                currencyLabel.textContent = columnType.currency;
                currencyLabel.style.position = 'absolute';
                currencyLabel.style.right = '15px';
                currencyLabel.style.top = '50%';
                currencyLabel.style.transform = 'translateY(-50%)';
                currencyLabel.style.color = '#666';
                currencyLabel.style.fontWeight = '500';
                currencyLabel.style.pointerEvents = 'none';

                currencyWrapper.appendChild(input);
                currencyWrapper.appendChild(currencyLabel);
                fieldContainer.appendChild(label);
                fieldContainer.appendChild(currencyWrapper);
            } else if (columnType.unit && columnType.type === 'number') {
                const unitWrapper = document.createElement('div');
                unitWrapper.style.position = 'relative';
                unitWrapper.style.display = 'inline-block';
                unitWrapper.style.width = '100%';
                unitWrapper.style.maxWidth = '600px';

                const unitLabel = document.createElement('span');
                unitLabel.textContent = columnType.unit;
                unitLabel.style.position = 'absolute';
                unitLabel.style.right = '15px';
                unitLabel.style.top = '50%';
                unitLabel.style.transform = 'translateY(-50%)';
                unitLabel.style.color = '#666';
                unitLabel.style.fontWeight = '500';
                unitLabel.style.pointerEvents = 'none';

                unitWrapper.appendChild(input);
                unitWrapper.appendChild(unitLabel);
                fieldContainer.appendChild(label);
                fieldContainer.appendChild(unitWrapper);
            } else {
                fieldContainer.appendChild(label);
                fieldContainer.appendChild(input);
            }

            // Add sample values hint if available
            if (columnType.sampleValues && columnType.sampleValues.length > 0) {
                const hint = document.createElement('div');
                hint.style.fontSize = '12px';
                hint.style.color = '#999';
                hint.style.marginTop = '4px';
                hint.style.fontStyle = 'italic';
                hint.textContent = `Sample: ${columnType.sampleValues.slice(0, 2).join(', ')}`;
                fieldContainer.appendChild(hint);
            }

            csvFormSection.appendChild(fieldContainer);
        });

        container.appendChild(csvFormSection);
    }

    // Loop through all keys in extracted data
    Object.entries(data).forEach(([key, value]) => {
        // Skip internal fields that shouldn't be displayed as form inputs
        if (key === 'imageUrl' || key === 'type' || key === 'message' || key === 'dimensions' ||
            key === 'imageType' || key === 'format' || key === 'mimeType' || key === 'ocrWords' ||
            key === 'hasText' || key === 'ocrConfidence' || key === 'ocrWordCount' || key === 'metadata' ||
            key === 'parsedFormData' || key === 'columnTypes' || key === 'firstRowData' ||
            key === 'headers' ||
            key === 'textLength' || key === 'pages' || key === 'rowCount' || key === 'columnCount' ||
            key === 'aiExtracted' || key === 'documentType' || key === 'ocrError' || key === 'warning' ||
            key === 'outputFormat' || key === 'url' || key === 'title' || key === 'description' ||
            key === 'hero' || key === 'navigation' || key === 'sections' || key === 'googleMap' ||
            key === 'floorPlans' || key === 'images' || key === 'ogData' || key === 'structuredData' ||
            key === 'textContent' || key === 'realEstateData' || key === 'urlsCrawled') {
            return;
        }

        // Handle PDF text field specially (before other text fields)
        if (key === 'text' && data.type === 'pdf') {
            // This is handled above in the extractedText section
            return;
        }

        const label = document.createElement('label');
        label.style.display = 'block';
        label.style.marginTop = '15px';
        label.style.fontWeight = '500';
        label.style.color = '#333';

        // Label text with formatting
        label.innerText = formatLabel(key);

        // Create input based on type or key
        let input;

        if (key === 'extractedText' || (key === 'text' && data.type === 'pdf')) {
            // OCR/PDF extracted text - special styling
            const textContainer = document.createElement('div');
            textContainer.style.marginTop = '10px';

            const textLabel = document.createElement('div');
            textLabel.style.marginBottom = '8px';
            textLabel.style.fontSize = '14px';
            textLabel.style.color = '#666';

            let labelText = data.type === 'pdf' ? 'PDF Extracted Text' : 'Raw Extracted Text';
            if (data.ocrConfidence && data.ocrConfidence !== 'N/A') {
                labelText += ` (OCR Confidence: ${data.ocrConfidence})`;
            }
            if (data.parsedFormData && (data.parsedFormData.fieldCount > 0 || (data.parsedFormData.sections && data.parsedFormData.sections.length > 0))) {
                const fieldCount = data.parsedFormData.fieldCount ||
                    (data.parsedFormData.sections ? data.parsedFormData.sections.reduce((sum, s) => sum + (s.fields ? s.fields.length : 0), 0) : 0);
                labelText += ` - ${fieldCount} fields detected`;
            }
            textLabel.innerHTML = labelText;
            textContainer.appendChild(textLabel);

            // Add note about dynamic form
            if (data.parsedFormData && (data.parsedFormData.fieldCount > 0 || (data.parsedFormData.sections && data.parsedFormData.sections.length > 0))) {
                const note = document.createElement('div');
                note.style.marginBottom = '10px';
                note.style.padding = '10px';
                note.style.backgroundColor = '#e3f2fd';
                note.style.borderRadius = '4px';
                note.style.fontSize = '13px';
                note.style.color = '#1976d2';
                note.innerHTML = '✓ Text parsed and dynamic form generated below. You can edit the raw text here if needed.';
                textContainer.appendChild(note);
            }

            input = document.createElement('textarea');
            input.rows = 8;
            input.value = value || (data.type === 'pdf' ? 'No text extracted from PDF' : 'No text extracted from image');
            input.style.width = '100%';
            input.style.maxWidth = '600px';
            input.style.padding = '10px';
            input.style.marginTop = '5px';
            input.style.border = '2px solid #4CAF50';
            input.style.borderRadius = '4px';
            input.style.fontSize = '14px';
            input.style.fontFamily = 'monospace';
            input.style.backgroundColor = value ? '#f1f8f4' : '#fff';

            textContainer.appendChild(input);
            label.appendChild(textContainer);
            container.appendChild(label);
            return;
        } else if (key === 'description' || key === 'bio' || key === 'text' || key === 'content') {
            // Long text fields
            input = document.createElement('textarea');
            input.rows = 6;
            input.value = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
        } else if (key === 'publish_date' || key === 'creationDate' || key === 'modificationDate' || key === 'uploadDate') {
            // Date input
            input = document.createElement('input');
            input.type = 'date';
            if (value) {
                const date = new Date(value);
                if (!isNaN(date)) {
                    input.value = date.toISOString().split('T')[0];
                }
            }
        } else if (key === 'images' && Array.isArray(value)) {
            // Multiple image URLs — create multiple input fields
            value.forEach((imgUrl, index) => {
                const imgLabel = document.createElement('label');
                imgLabel.style.display = 'block';
                imgLabel.style.fontWeight = 'normal';
                imgLabel.style.marginLeft = '20px';
                imgLabel.style.marginTop = '10px';
                imgLabel.innerText = `image [${index + 1}]`;

                const imgInput = document.createElement('input');
                imgInput.type = 'text';
                imgInput.value = imgUrl;
                imgInput.name = `images[${index}]`;
                imgInput.style.width = '100%';
                imgInput.style.maxWidth = '600px';

                imgLabel.appendChild(imgInput);
                container.appendChild(imgLabel);
            });
            return;
        } else if (key === 'rows' && Array.isArray(value)) {
            // CSV rows - display as table
            const tableDiv = document.createElement('div');
            tableDiv.style.marginTop = '10px';
            tableDiv.style.overflowX = 'auto';

            const table = document.createElement('table');
            table.style.borderCollapse = 'collapse';
            table.style.width = '100%';
            table.style.border = '1px solid #ddd';

            // Add headers if available
            if (data.headers && Array.isArray(data.headers)) {
                const headerRow = document.createElement('tr');
                data.headers.forEach(header => {
                    const th = document.createElement('th');
                    th.textContent = header;
                    th.style.padding = '10px';
                    th.style.border = '1px solid #ddd';
                    th.style.backgroundColor = '#f5f5f5';
                    headerRow.appendChild(th);
                });
                table.appendChild(headerRow);
            }

            // Add rows (limit to first 20 for performance)
            value.slice(0, 20).forEach(row => {
                const tr = document.createElement('tr');
                Object.values(row).forEach(cell => {
                    const td = document.createElement('td');
                    td.textContent = cell || '';
                    td.style.padding = '8px';
                    td.style.border = '1px solid #ddd';
                    tr.appendChild(td);
                });
                table.appendChild(tr);
            });

            tableDiv.appendChild(table);
            if (value.length > 20) {
                const note = document.createElement('p');
                note.style.marginTop = '10px';
                note.style.color = '#666';
                note.style.fontSize = '14px';
                note.textContent = `Showing first 20 of ${value.length} rows`;
                tableDiv.appendChild(note);
            }

            label.appendChild(tableDiv);
            container.appendChild(label);
            return;
        } else if (key === 'preview' && Array.isArray(value)) {
            // Preview data (like CSV preview)
            const previewDiv = document.createElement('div');
            previewDiv.style.marginTop = '10px';
            previewDiv.style.padding = '10px';
            previewDiv.style.backgroundColor = '#f9f9f9';
            previewDiv.style.borderRadius = '4px';
            previewDiv.style.fontSize = '14px';
            previewDiv.textContent = JSON.stringify(value, null, 2);
            label.appendChild(previewDiv);
            container.appendChild(label);
            return;
        } else if (key === 'ocrWords' && Array.isArray(value)) {
            // OCR words with confidence - display as table
            const wordsDiv = document.createElement('div');
            wordsDiv.style.marginTop = '10px';
            wordsDiv.style.maxHeight = '300px';
            wordsDiv.style.overflowY = 'auto';

            const wordsTable = document.createElement('table');
            wordsTable.style.borderCollapse = 'collapse';
            wordsTable.style.width = '100%';
            wordsTable.style.border = '1px solid #ddd';
            wordsTable.style.fontSize = '13px';

            // Header
            const headerRow = document.createElement('tr');
            ['Text', 'Confidence', 'Bounding Box'].forEach(headerText => {
                const th = document.createElement('th');
                th.textContent = headerText;
                th.style.padding = '8px';
                th.style.border = '1px solid #ddd';
                th.style.backgroundColor = '#e8f5e9';
                th.style.textAlign = 'left';
                headerRow.appendChild(th);
            });
            wordsTable.appendChild(headerRow);

            // Words (limit to first 100)
            value.slice(0, 100).forEach(word => {
                const tr = document.createElement('tr');

                const tdText = document.createElement('td');
                tdText.textContent = word.text || '';
                tdText.style.padding = '6px';
                tdText.style.border = '1px solid #ddd';
                tr.appendChild(tdText);

                const tdConf = document.createElement('td');
                tdConf.textContent = word.confidence || 'N/A';
                tdConf.style.padding = '6px';
                tdConf.style.border = '1px solid #ddd';
                tr.appendChild(tdConf);

                const tdBbox = document.createElement('td');
                tdBbox.textContent = word.bbox ? `x:${word.bbox.x0}, y:${word.bbox.y0}, w:${word.bbox.x1 - word.bbox.x0}, h:${word.bbox.y1 - word.bbox.y0}` : 'N/A';
                tdBbox.style.padding = '6px';
                tdBbox.style.border = '1px solid #ddd';
                tdBbox.style.fontSize = '12px';
                tdBbox.style.color = '#666';
                tr.appendChild(tdBbox);

                wordsTable.appendChild(tr);
            });

            wordsDiv.appendChild(wordsTable);
            if (value.length > 100) {
                const note = document.createElement('p');
                note.style.marginTop = '10px';
                note.style.color = '#666';
                note.style.fontSize = '12px';
                note.textContent = `Showing first 100 of ${value.length} words`;
                wordsDiv.appendChild(note);
            }

            label.appendChild(wordsDiv);
            container.appendChild(label);
            return;
        } else if (key === 'metadata' && typeof value === 'object') {
            // Metadata object - display as JSON
            input = document.createElement('textarea');
            input.rows = 8;
            input.value = JSON.stringify(value, null, 2);
        } else if (key === 'parsedData' && typeof value === 'object') {
            // Parsed JSON data
            input = document.createElement('textarea');
            input.rows = 10;
            input.value = JSON.stringify(value, null, 2);
        } else if (Array.isArray(value)) {
            // Array values - display as JSON
            input = document.createElement('textarea');
            input.rows = 6;
            input.value = JSON.stringify(value, null, 2);
        } else if (typeof value === 'object' && value !== null) {
            // Object values - display as JSON
            input = document.createElement('textarea');
            input.rows = 8;
            input.value = JSON.stringify(value, null, 2);
        } else {
            // Default to single line text input
            input = document.createElement('input');
            input.type = 'text';
            input.value = value !== null && value !== undefined ? String(value) : '';
        }

        input.name = key;
        input.className = 'data-input'; // Ensure we have a class for inputs if needed

        label.appendChild(input);
        container.appendChild(label);
    });

    // Action buttons container
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'projects-toolbar';
    buttonContainer.style.marginTop = '2rem';

    // Submit button
    const submitBtn = document.createElement('button');
    submitBtn.innerText = 'Submit';
    submitBtn.className = 'btn-primary';
    submitBtn.style.flex = '1';
    submitBtn.onclick = () => {
        const formData = getLiveFormData(container, currentExtractedData);
        console.log('Form Data:', formData);
        alert('Form submitted! Check console for data.');
    };
    buttonContainer.appendChild(submitBtn);

    // Save as Project button
    const saveProjectBtn = document.createElement('button');
    saveProjectBtn.innerText = currentProjectId ? 'Update Project' : 'Save as Project';
    saveProjectBtn.className = 'btn-secondary';
    saveProjectBtn.style.flex = '1';
    saveProjectBtn.onclick = () => {
        const liveData = getLiveFormData(container, currentExtractedData);
        if (currentProjectId) {
            updateExistingProject(currentProjectId, liveData);
            return;
        }
        saveAsProject(liveData);
    };
    buttonContainer.appendChild(saveProjectBtn);

    container.appendChild(buttonContainer);
}

// Format label text (convert camelCase to Title Case)
function formatLabel(key) {
    return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

function isProjectSchemaData(data) {
    return !!(data &&
        typeof data === 'object' &&
        data.hero_section &&
        data.about &&
        data.location &&
        data.project_info &&
        data.contact);
}

function renderProjectSchemaForm(container, data) {
    const skipKeys = ['documents'];
    Object.entries(data).forEach(([key, value]) => {
        if (skipKeys.includes(key)) return;
        container.appendChild(createNestedField(key, value, key, 0));
    });
}

function createNestedField(key, value, path, depth) {
    const wrapper = document.createElement('div');
    wrapper.style.marginTop = depth === 0 ? '1rem' : '0.75rem';

    // Nested object: render children as grouped fields
    if (value && typeof value === 'object' && !Array.isArray(value)) {
        const header = createSectionHeader(formatLabel(key), true);
        wrapper.appendChild(header.container);

        const group = document.createElement('div');
        group.style.padding = '0.75rem';
        group.style.border = '1px solid var(--border)';
        group.style.borderRadius = '10px';
        group.style.background = 'var(--bg)';
        group.style.marginTop = '0.45rem';

        Object.entries(value).forEach(([childKey, childValue]) => {
            const childPath = `${path}.${childKey}`;
            group.appendChild(createNestedField(childKey, childValue, childPath, depth + 1));
        });

        wrapper.appendChild(group);
        header.setContent(group);
        return wrapper;
    }

    // Arrays
    if (Array.isArray(value)) {
        const header = createSectionHeader(formatLabel(key), true);
        wrapper.appendChild(header.container);

        const group = document.createElement('div');
        group.style.padding = '0.75rem';
        group.style.border = '1px solid var(--border)';
        group.style.borderRadius = '10px';
        group.style.background = 'var(--bg)';
        group.style.marginTop = '0.45rem';

        if (value.length === 0) {
            const emptyInput = document.createElement('input');
            emptyInput.type = 'text';
            emptyInput.name = path;
            emptyInput.value = '';
            emptyInput.placeholder = '[]';
            group.appendChild(emptyInput);
        } else {
            value.forEach((item, index) => {
                const itemPath = `${path}[${index}]`;
                if (item && typeof item === 'object') {
                    group.appendChild(createNestedField(`item_${index + 1}`, item, itemPath, depth + 1));
                } else {
                    const itemLabel = document.createElement('label');
                    itemLabel.style.display = 'block';
                    itemLabel.style.fontWeight = '500';
                    itemLabel.style.marginTop = index === 0 ? '0' : '0.5rem';
                    itemLabel.textContent = `${formatLabel(key)} ${index + 1}`;

                    const itemInput = document.createElement('input');
                    itemInput.type = 'text';
                    itemInput.name = itemPath;
                    itemInput.value = item !== null && item !== undefined ? String(item) : '';
                    itemInput.style.marginTop = '0.3rem';

                    itemLabel.appendChild(itemInput);
                    group.appendChild(itemLabel);
                }
            });
        }

        wrapper.appendChild(group);
        header.setContent(group);
        return wrapper;
    }

    const label = document.createElement('label');
    label.style.display = 'block';
    label.style.fontWeight = depth === 0 ? '700' : '600';
    label.style.color = 'var(--text-main)';
    label.style.marginBottom = '0.4rem';
    label.textContent = formatLabel(key);
    wrapper.appendChild(label);

    // Primitive values
    const isLongText = typeof value === 'string' && (
        value.length > 120 ||
        /description|content|disclaimer|policy|terms/i.test(key)
    );

    let input;
    if (isLongText) {
        input = document.createElement('textarea');
        input.rows = 4;
    } else {
        input = document.createElement('input');
        input.type = 'text';
    }
    input.name = path;
    input.value = value !== null && value !== undefined ? String(value) : '';
    wrapper.appendChild(input);

    return wrapper;
}

function createSectionHeader(title, collapsedByDefault) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.gap = '0.5rem';

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'btn-outline';
    toggle.style.padding = '0.15rem 0.35rem';
    toggle.style.minWidth = '26px';
    toggle.style.height = '24px';
    toggle.style.lineHeight = '1';
    toggle.style.fontSize = '12px';
    toggle.style.borderRadius = '6px';
    toggle.textContent = collapsedByDefault ? '▶' : '▼';

    const label = document.createElement('label');
    label.style.display = 'block';
    label.style.fontWeight = '700';
    label.style.color = 'var(--text-main)';
    label.style.marginBottom = '0';
    label.textContent = title;

    container.appendChild(toggle);
    container.appendChild(label);

    let content = null;
    let collapsed = collapsedByDefault;

    const updateState = () => {
        toggle.textContent = collapsed ? '▶' : '▼';
        if (content) {
            content.style.display = collapsed ? 'none' : 'block';
        }
    };

    toggle.addEventListener('click', () => {
        collapsed = !collapsed;
        updateState();
    });

    return {
        container,
        setContent(node) {
            content = node;
            updateState();
        }
    };
}

function parsePathTokens(path) {
    const tokens = [];
    const re = /([^[.\]]+)|\[(\d+)\]/g;
    let match;
    while ((match = re.exec(path)) !== null) {
        if (match[1] !== undefined) {
            tokens.push(match[1]);
        } else if (match[2] !== undefined) {
            tokens.push(Number(match[2]));
        }
    }
    return tokens;
}

function setValueByPath(target, path, value) {
    if (!path) return;
    const tokens = parsePathTokens(path);
    if (tokens.length === 0) return;

    let cursor = target;
    for (let i = 0; i < tokens.length; i++) {
        const token = tokens[i];
        const isLast = i === tokens.length - 1;
        const nextToken = tokens[i + 1];

        if (isLast) {
            cursor[token] = value;
            return;
        }

        if (cursor[token] === undefined || cursor[token] === null) {
            cursor[token] = typeof nextToken === 'number' ? [] : {};
        }
        cursor = cursor[token];
    }
}

function getLiveFormData(container, fallbackData = {}) {
    let snapshot = {};
    try {
        snapshot = JSON.parse(JSON.stringify(fallbackData || {}));
    } catch {
        snapshot = { ...(fallbackData || {}) };
    }

    container.querySelectorAll('input[name], textarea[name], select[name]').forEach(input => {
        const name = input.name;
        if (!name) return;

        let value;
        if (input.type === 'checkbox') {
            value = !!input.checked;
        } else {
            value = input.value;
        }

        setValueByPath(snapshot, name, value);
    });

    return snapshot;
}

// ==================== PROJECTS MANAGEMENT ====================

// Load and display projects
async function loadProjects() {
    const list = document.getElementById('projectsList');
    const container = document.getElementById('projectsContainer');

    // Show container if it's hidden
    if (container && (container.style.display === 'none' || container.style.display === '')) {
        container.style.display = 'block';
    }

    // Show refresh button
    const refreshBtn = document.getElementById('refreshProjectsBtn');
    if (refreshBtn) {
        refreshBtn.style.display = 'inline-block';
    }

    list.innerHTML = '<p>Loading projects...</p>';

    try {
        // Fetch with higher limit to get all projects
        const response = await fetch('http://localhost:3000/api/projects?skip=0&limit=1000');
        if (!response.ok) throw new Error('Failed to load projects');

        const data = await response.json();
        const projects = data.projects || [];

        if (projects.length === 0) {
            list.innerHTML = '<p>No projects found. Create a project by extracting data from a URL or file.</p>';
            return;
        }

        list.innerHTML = projects.map(project => `
            <div class="project-card">
                <div class="project-header">
                    <div class="project-name">${project.project_name || 'Unnamed Project'}</div>
                </div>
                <div class="project-actions">
                    <button class="btn-outline" style="flex: 1;" onclick="fetchWebsiteForProject(${project.id}, this)">Fetch</button>
                    <button class="btn-outline" style="flex: 1;" onclick="addDocumentToProject(${project.id}, this)">Doc</button>
                    <button class="btn-primary" style="flex: 1;" onclick="viewProject(${project.id})">View</button>
                    <button class="btn-danger" style="flex: 1;" onclick="deleteProject(${project.id})">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        list.innerHTML = `<p style="color: red;">Error loading projects: ${error.message}</p>`;
    }
}

// Always load projects list on page open.
loadProjects();

// Fetch website for a project
function openFetchWebsiteModal(projectId, triggerButtonEl = null) {
    closeModal();

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'projectActionModal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2>Fetch Website for Project</h2>
            <div class="modal-body">
                <p style="margin-bottom: 12px; color: #666; font-size: 14px;">
                    Upsert mode: this will update only null/empty fields in this same project.
                </p>
                <input type="url" id="projectFetchUrl" placeholder="https://example.com/project-page" style="width: 100%; margin-bottom: 12px;" />
                <div style="display:flex; gap:10px; justify-content:flex-end;">
                    <button class="btn-outline" onclick="closeModal()">Cancel</button>
                    <button class="btn-primary" onclick="fetchWebsiteForProject(${projectId}, this, document.getElementById('projectFetchUrl').value, true)">Fetch & Upsert</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    const input = document.getElementById('projectFetchUrl');
    if (input) {
        input.focus();
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const modalBtn = modal.querySelector('.btn-primary');
                if (modalBtn) {
                    fetchWebsiteForProject(projectId, modalBtn, input.value, true);
                }
            }
        });
    }

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
}

async function fetchWebsiteForProject(projectId, buttonEl = null, urlValue = '', closeOnSuccess = false) {
    const url = (urlValue || '').trim();
    if (!url) {
        openFetchWebsiteModal(projectId, buttonEl);
        return;
    }

    const btn = buttonEl || event?.target || null;
    const originalText = btn ? btn.innerText : null;
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Fetching...';
    }

    try {
        const response = await fetch(`http://localhost:3000/api/projects/${projectId}/fetch-website`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, multi_page: false, max_pages: 5 })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to fetch website');
        }

        const data = await response.json();
        alert('Website data fetched and merged successfully!');
        if (data?.project) {
            generateForm(data.project, { projectId });
        }
        if (closeOnSuccess) {
            closeModal();
        }

        // Ensure projects container is visible and refresh
        const container = document.getElementById('projectsContainer');
        if (container) {
            container.style.display = 'block';
        }
        await loadProjects(); // Refresh list
    } catch (error) {
        alert('Error fetching website: ' + error.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = originalText;
        }
    }
}

// Add document to a project
async function addDocumentToProject(projectId, triggerButtonEl = null) {
    closeModal();

    // Create modal for file upload
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'projectActionModal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2>Add Document to Project</h2>
            <div class="modal-body">
                <p style="margin-bottom: 12px; color: #666; font-size: 14px;">
                    Upsert mode: this will update only null/empty fields in this same project.
                </p>
                <input type="file" id="projectFileInput" accept=".pdf,.txt,.json,.csv,.md,.jpg,.jpeg,.png,.gif,.webp,.bmp"/>
                <div style="display:flex; gap:10px; justify-content:flex-end; margin-top:12px;">
                    <button class="btn-outline" onclick="closeModal()">Cancel</button>
                    <button class="btn-primary" onclick="uploadDocumentToProject(${projectId}, this)">Upload & Upsert</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });
}

function closeModal() {
    const modal = document.getElementById('projectActionModal');
    if (modal) {
        modal.style.display = 'none';
        modal.remove();
    }
}

async function uploadDocumentToProject(projectId, buttonEl = null) {
    const fileInput = document.getElementById('projectFileInput');
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a file');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const btn = buttonEl || event?.target || null;
    const originalText = btn ? btn.innerText : null;
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Uploading...';
    }

    try {
        const response = await fetch(`http://localhost:3000/api/projects/${projectId}/add-document`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to upload document');
        }

        const data = await response.json();
        alert('Document uploaded and data merged successfully!');
        if (data?.project) {
            generateForm(data.project, { projectId });
        }
        closeModal();

        // Ensure projects container is visible and refresh
        const container = document.getElementById('projectsContainer');
        if (container) {
            container.style.display = 'block';
        }
        await loadProjects(); // Refresh list
    } catch (error) {
        alert('Error uploading document: ' + error.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = originalText;
        }
    }
}

// View project details
async function viewProject(projectId) {
    try {
        const response = await fetch(`http://localhost:3000/api/projects/${projectId}`);
        if (!response.ok) throw new Error('Failed to load project');

        const project = await response.json();

        // Show project data in form container
        generateForm(project, { projectId });

        // Scroll to form
        document.getElementById('formContainer').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        alert('Error loading project: ' + error.message);
    }
}

// Delete project
async function deleteProject(projectId) {
    const confirmed = confirm('Delete this project permanently? This action cannot be undone.');
    if (!confirmed) return;

    try {
        const response = await fetch(`http://localhost:3000/api/projects/${projectId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to delete project');
        }

        await loadProjects();
        alert('Project deleted successfully.');
    } catch (error) {
        alert('Error deleting project: ' + error.message);
    }
}

// Save extracted data as a new project
async function saveAsProject(data) {
    if (!data) {
        alert('No data to save');
        return;
    }

    if (isSavingProject) return;
    if (hasSavedCurrentExtraction) {
        alert('This data is already saved once. Extract/view new data to save again.');
        return;
    }

    const projectData = getProjectPayloadForPersistence(data);

    // If this is already in project schema format (has hero_section, about, etc.)
    // and doesn't have url/realEstateData, it's already mapped
    // Otherwise, let backend handle mapping

    // Debug: Log what we're sending
    console.log('Saving project with data:', projectData);
    console.log('Data keys:', Object.keys(projectData));
    console.log('Has url/realEstateData?', !!projectData.url || !!projectData.realEstateData);
    console.log('Has parsedFormData?', !!projectData.parsedFormData);
    console.log('Has hero_section/about/location?', !!(projectData.hero_section || projectData.about || projectData.location));

    // Create project
    try {
        isSavingProject = true;
        const response = await fetch('http://localhost:3000/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_data: projectData })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to save project');
        }

        const result = await response.json();
        alert('Project saved successfully!');
        hasSavedCurrentExtraction = true;

        // Ensure projects container is visible and refresh
        const container = document.getElementById('projectsContainer');
        if (container) {
            container.style.display = 'block';
        }
        await loadProjects(); // Refresh projects list
    } catch (error) {
        alert('Error saving project: ' + error.message);
        console.error('Save error:', error);
        console.error('Data being saved:', projectData);
    } finally {
        isSavingProject = false;
    }
}

function getProjectPayloadForPersistence(data) {
    const metadataFields = ['id', 'created_at', 'updated_at', 'documents'];
    const payload = { ...(data || {}) };
    metadataFields.forEach(field => {
        delete payload[field];
    });
    return payload;
}

// Update an existing project row. Backend upsert only fills null/empty values.
async function updateExistingProject(projectId, data) {
    if (!projectId) {
        alert('Project id is missing for update');
        return;
    }
    if (!data) {
        alert('No data to update');
        return;
    }
    if (isSavingProject) return;

    const projectData = getProjectPayloadForPersistence(data);

    try {
        isSavingProject = true;
        const response = await fetch(`http://localhost:3000/api/projects/${projectId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_data: projectData })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to update project');
        }

        const result = await response.json();
        alert('Project updated successfully! (Only null/empty fields were filled)');
        if (result?.project) {
            generateForm(result.project, { projectId: result.project.id || projectId });
        }

        const container = document.getElementById('projectsContainer');
        if (container) {
            container.style.display = 'block';
        }
        await loadProjects();
    } catch (error) {
        alert('Error updating project: ' + error.message);
        console.error('Update error:', error);
    } finally {
        isSavingProject = false;
    }
}

