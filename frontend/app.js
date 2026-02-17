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
    fetchBtn.innerHTML = 'Fetching... <span class="loading"></span>';

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
let selectedFile = null;

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
    fileInfo.classList.add('show');
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
    uploadBtn.innerHTML = 'Processing... <span class="loading"></span>';

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
        fileInfo.classList.remove('show');
        uploadBtn.style.display = 'none';
    } catch (error) {
        alert('Error processing file: ' + error.message);
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerText = originalText;
    }
});

function generateForm(data) {
    const container = document.getElementById('formContainer');
    container.innerHTML = ''; // clear previous

    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<p style="color: #999;">No data extracted.</p>';
        return;
    }

    // Handle error cases
    if (data.error) {
        const errorDiv = document.createElement('div');
        errorDiv.style.padding = '15px';
        errorDiv.style.backgroundColor = '#ffebee';
        errorDiv.style.borderRadius = '6px';
        errorDiv.style.color = '#c62828';
        errorDiv.innerHTML = `<strong>Error:</strong> ${data.message || data.error}`;
        container.appendChild(errorDiv);
        return;
    }

    // Special handling for image data - display image preview first
    if (data.type === 'image' && data.imageUrl) {
        const imageSection = document.createElement('div');
        imageSection.style.marginBottom = '30px';
        imageSection.style.padding = '20px';
        imageSection.style.backgroundColor = '#f9f9f9';
        imageSection.style.borderRadius = '8px';
        imageSection.style.border = '1px solid #ddd';
        
        const imageTitle = document.createElement('h3');
        imageTitle.textContent = 'Image Preview';
        imageTitle.style.marginBottom = '15px';
        imageTitle.style.color = '#333';
        imageSection.appendChild(imageTitle);
        
        const img = document.createElement('img');
        img.src = `http://localhost:3000${data.imageUrl}`;
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
        img.style.borderRadius = '6px';
        img.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        img.alt = data.filename || 'Uploaded image';
        imageSection.appendChild(img);
        
        // Image type and format info
        if (data.imageType || data.format) {
            const typeInfo = document.createElement('div');
            typeInfo.style.marginTop = '15px';
            typeInfo.style.padding = '10px';
            typeInfo.style.backgroundColor = '#e3f2fd';
            typeInfo.style.borderRadius = '4px';
            typeInfo.style.fontSize = '14px';
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
            ocrErrorDiv.style.marginTop = '15px';
            ocrErrorDiv.style.padding = '15px';
            ocrErrorDiv.style.backgroundColor = '#fff3e0';
            ocrErrorDiv.style.borderRadius = '6px';
            ocrErrorDiv.style.borderLeft = '4px solid #ff9800';
            ocrErrorDiv.style.fontSize = '14px';
            ocrErrorDiv.style.color = '#e65100';
            ocrErrorDiv.innerHTML = `
                <strong>⚠ OCR Warning:</strong> ${data.ocrError}
                ${data.warning ? `<br><span style="font-size: 12px; margin-top: 5px; display: block;">${data.warning}</span>` : ''}
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

    // Generate dynamic form from parsed text data (for images with OCR)
    if (data.parsedFormData && data.parsedFormData.sections && data.parsedFormData.sections.length > 0) {
        const formSection = document.createElement('div');
        formSection.style.marginTop = '30px';
        formSection.style.marginBottom = '30px';
        
        const formTitle = document.createElement('h2');
        formTitle.textContent = 'Dynamic Form (Generated from Extracted Text)';
        formTitle.style.color = '#333';
        formTitle.style.marginBottom = '10px';
        formTitle.style.fontSize = '20px';
        formSection.appendChild(formTitle);
        
        // Add summary info
        const summaryInfo = document.createElement('div');
        summaryInfo.style.marginBottom = '25px';
        summaryInfo.style.padding = '12px 15px';
        summaryInfo.style.backgroundColor = '#e3f2fd';
        summaryInfo.style.borderRadius = '6px';
        summaryInfo.style.borderLeft = '4px solid #2196f3';
        summaryInfo.style.fontSize = '14px';
        summaryInfo.style.color = '#1976d2';
        
        const totalFields = data.parsedFormData.fieldCount || 0;
        const totalSections = data.parsedFormData.sections ? data.parsedFormData.sections.length : 0;
        summaryInfo.innerHTML = `
            <strong>✓ Successfully extracted ${totalFields} field${totalFields !== 1 ? 's' : ''}</strong> 
            ${totalSections > 0 ? `organized into ${totalSections} section${totalSections !== 1 ? 's' : ''}` : ''}
            <br>
            <span style="font-size: 12px; color: #1565c0;">Each field shows a clear Label (Key) and Value pair for easy editing</span>
        `;
        formSection.appendChild(summaryInfo);
        
        data.parsedFormData.sections.forEach((section, sectionIndex) => {
            // Section header
            if (section.title && section.title !== 'Extracted Data') {
                const sectionHeader = document.createElement('h3');
                sectionHeader.textContent = section.title;
                sectionHeader.style.color = '#555';
                sectionHeader.style.marginTop = sectionIndex > 0 ? '25px' : '0';
                sectionHeader.style.marginBottom = '15px';
                sectionHeader.style.paddingBottom = '10px';
                sectionHeader.style.borderBottom = '2px solid #4CAF50';
                sectionHeader.style.fontSize = '18px';
                formSection.appendChild(sectionHeader);
            }
            
            // Generate form fields for this section
            section.fields.forEach((field, fieldIndex) => {
                if (field.isHeader) return; // Skip header fields as they're already displayed
                
                const fieldContainer = document.createElement('div');
                fieldContainer.style.marginBottom = '20px';
                fieldContainer.style.padding = '15px';
                fieldContainer.style.backgroundColor = '#fafafa';
                fieldContainer.style.borderRadius = '8px';
                fieldContainer.style.border = '1px solid #e0e0e0';
                fieldContainer.style.transition = 'all 0.3s ease';
                
                // Hover effect
                fieldContainer.addEventListener('mouseenter', () => {
                    fieldContainer.style.backgroundColor = '#f5f5f5';
                    fieldContainer.style.borderColor = '#4CAF50';
                });
                fieldContainer.addEventListener('mouseleave', () => {
                    fieldContainer.style.backgroundColor = '#fafafa';
                    fieldContainer.style.borderColor = '#e0e0e0';
                });
                
                // Create a key-value display structure
                const keyValueRow = document.createElement('div');
                keyValueRow.style.display = 'flex';
                keyValueRow.style.alignItems = 'flex-start';
                keyValueRow.style.gap = '15px';
                keyValueRow.style.marginBottom = '10px';
                
                // Key (Label) section
                const keySection = document.createElement('div');
                keySection.style.minWidth = '150px';
                keySection.style.maxWidth = '200px';
                keySection.style.flexShrink = '0';
                
                const keyLabel = document.createElement('div');
                keyLabel.textContent = 'Label:';
                keyLabel.style.fontSize = '11px';
                keyLabel.style.color = '#666';
                keyLabel.style.textTransform = 'uppercase';
                keyLabel.style.letterSpacing = '0.5px';
                keyLabel.style.marginBottom = '4px';
                keySection.appendChild(keyLabel);
                
                const keyValue = document.createElement('div');
                keyValue.textContent = field.label || `Field ${fieldIndex + 1}`;
                keyValue.style.fontWeight = '600';
                keyValue.style.color = '#1976d2';
                keyValue.style.fontSize = '14px';
                keyValue.style.wordBreak = 'break-word';
                keySection.appendChild(keyValue);
                
                // Add type badge if available
                if (field.type && field.type !== 'text') {
                    const typeBadge = document.createElement('span');
                    typeBadge.textContent = field.type;
                    typeBadge.style.display = 'inline-block';
                    typeBadge.style.marginTop = '4px';
                    typeBadge.style.padding = '2px 6px';
                    typeBadge.style.backgroundColor = '#4CAF50';
                    typeBadge.style.color = 'white';
                    typeBadge.style.borderRadius = '10px';
                    typeBadge.style.fontSize = '10px';
                    typeBadge.style.fontWeight = '500';
                    keyValue.appendChild(document.createElement('br'));
                    keyValue.appendChild(typeBadge);
                }
                
                // Value section
                const valueSection = document.createElement('div');
                valueSection.style.flex = '1';
                valueSection.style.minWidth = '0';
                
                const valueLabel = document.createElement('div');
                valueLabel.textContent = 'Value:';
                valueLabel.style.fontSize = '11px';
                valueLabel.style.color = '#666';
                valueLabel.style.textTransform = 'uppercase';
                valueLabel.style.letterSpacing = '0.5px';
                valueLabel.style.marginBottom = '4px';
                valueSection.appendChild(valueLabel);
                
                // Create the actual input field
                const label = document.createElement('label');
                label.style.display = 'none'; // Hide the old label, we're using key-value display
                
                let input;
                
                // Create input based on detected type
                switch (field.type) {
                    case 'number':
                        input = document.createElement('input');
                        input.type = 'number';
                        input.value = field.value || '';
                        input.step = field.unit === '%' ? '0.01' : '0.01';
                        if (field.currency) {
                            input.style.paddingRight = '60px';
                        }
                        if (field.unit) {
                            label.textContent += ` (${field.unit})`;
                        }
                        break;
                    case 'date':
                        input = document.createElement('input');
                        input.type = 'date';
                        input.value = field.value || '';
                        break;
                    case 'email':
                        input = document.createElement('input');
                        input.type = 'email';
                        input.value = field.value || '';
                        break;
                    case 'tel':
                        input = document.createElement('input');
                        input.type = 'tel';
                        input.value = field.value || '';
                        break;
                    default:
                        input = document.createElement('input');
                        input.type = 'text';
                        input.value = field.value || '';
                }
                
                // Common input styling
                input.name = field.id || `field_${sectionIndex}_${fieldIndex}`;
                input.style.width = '100%';
                input.style.padding = '12px';
                input.style.border = '2px solid #ddd';
                input.style.borderRadius = '6px';
                input.style.fontSize = '14px';
                input.style.transition = 'border-color 0.3s';
                input.style.backgroundColor = '#fff';
                
                input.addEventListener('focus', () => {
                    input.style.borderColor = '#4CAF50';
                    input.style.outline = 'none';
                });
                
                input.addEventListener('blur', () => {
                    input.style.borderColor = '#ddd';
                });
                
                // Add currency indicator if present
                let inputWrapper = input;
                if (field.currency && field.type === 'number') {
                    const currencyWrapper = document.createElement('div');
                    currencyWrapper.style.position = 'relative';
                    currencyWrapper.style.width = '100%';
                    
                    const currencyLabel = document.createElement('span');
                    currencyLabel.textContent = field.currency;
                    currencyLabel.style.position = 'absolute';
                    currencyLabel.style.right = '15px';
                    currencyLabel.style.top = '50%';
                    currencyLabel.style.transform = 'translateY(-50%)';
                    currencyLabel.style.color = '#666';
                    currencyLabel.style.fontWeight = '500';
                    currencyLabel.style.pointerEvents = 'none';
                    
                    currencyWrapper.appendChild(input);
                    currencyWrapper.appendChild(currencyLabel);
                    inputWrapper = currencyWrapper;
                }
                
                valueSection.appendChild(inputWrapper);
                
                // Combine key and value sections
                keyValueRow.appendChild(keySection);
                keyValueRow.appendChild(valueSection);
                fieldContainer.appendChild(keyValueRow);
                
                // Add original line as tooltip/hint (only if different from extracted value)
                if (field.originalLine && field.originalLine.trim() !== String(field.value || '').trim()) {
                    const hint = document.createElement('div');
                    hint.style.marginTop = '10px';
                    hint.style.padding = '8px';
                    hint.style.backgroundColor = '#fff3cd';
                    hint.style.borderRadius = '4px';
                    hint.style.borderLeft = '3px solid #ffc107';
                    hint.style.fontSize = '12px';
                    hint.style.color = '#856404';
                    hint.innerHTML = `<strong>Original text:</strong> <span style="font-family: monospace;">${field.originalLine}</span>`;
                    fieldContainer.appendChild(hint);
                }
                
                formSection.appendChild(fieldContainer);
            });
        });
        
        container.appendChild(formSection);
        
        // Don't process parsedFormData in the main loop
        if (data.parsedFormData) {
            // Skip it in main loop
        }
    }

    // Generate dynamic form from CSV data with type-specific inputs
    if (data.type === 'csv' && data.headers && data.columnTypes && data.firstRowData) {
        const csvFormSection = document.createElement('div');
        csvFormSection.style.marginTop = '30px';
        csvFormSection.style.marginBottom = '30px';
        csvFormSection.style.padding = '25px';
        csvFormSection.style.backgroundColor = '#f9f9f9';
        csvFormSection.style.borderRadius = '8px';
        csvFormSection.style.border = '2px solid #4CAF50';
        
        const formTitle = document.createElement('h2');
        formTitle.textContent = 'Dynamic Form (Generated from CSV)';
        formTitle.style.color = '#333';
        formTitle.style.marginBottom = '20px';
        formTitle.style.fontSize = '20px';
        csvFormSection.appendChild(formTitle);
        
        const infoNote = document.createElement('div');
        infoNote.style.marginBottom = '20px';
        infoNote.style.padding = '12px';
        infoNote.style.backgroundColor = '#e3f2fd';
        infoNote.style.borderRadius = '6px';
        infoNote.style.fontSize = '14px';
        infoNote.style.color = '#1976d2';
        infoNote.innerHTML = `✓ Form generated with ${data.headers.length} fields. Pre-filled with first row data (${data.rowCount} total rows available).`;
        csvFormSection.appendChild(infoNote);
        
        // Generate form fields for each column
        data.headers.forEach((header, index) => {
            const columnType = data.columnTypes[header] || { type: 'text', unit: null, currency: null };
            const fieldValue = data.firstRowData[header] || '';
            
            const fieldContainer = document.createElement('div');
            fieldContainer.style.marginBottom = '20px';
            
            const label = document.createElement('label');
            label.textContent = header;
            label.style.display = 'block';
            label.style.fontWeight = '500';
            label.style.color = '#333';
            label.style.marginBottom = '8px';
            label.style.fontSize = '14px';
            
            // Add type indicator
            const typeBadge = document.createElement('span');
            typeBadge.textContent = columnType.type;
            typeBadge.style.marginLeft = '10px';
            typeBadge.style.padding = '2px 8px';
            typeBadge.style.backgroundColor = '#4CAF50';
            typeBadge.style.color = 'white';
            typeBadge.style.borderRadius = '12px';
            typeBadge.style.fontSize = '11px';
            typeBadge.style.fontWeight = '500';
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
            key === 'headers' || key === 'rows' || key === 'preview' ||
            key === 'textLength' || key === 'pages' || key === 'rowCount' || key === 'columnCount' ||
            key === 'aiExtracted' || key === 'documentType' || key === 'ocrError' || key === 'warning') {
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
        input.style.width = '100%';
        input.style.maxWidth = '600px';
        input.style.padding = '10px';
        input.style.marginTop = '5px';
        input.style.border = '1px solid #ddd';
        input.style.borderRadius = '4px';
        input.style.fontSize = '14px';
        
        label.appendChild(input);
        container.appendChild(label);
    });

    // Submit button
    const submitBtn = document.createElement('button');
    submitBtn.innerText = 'Submit';
    submitBtn.style.marginTop = '20px';
    submitBtn.onclick = () => {
        const formData = {};
        container.querySelectorAll('input, textarea').forEach(input => {
            if (input.name && input.value) {
                formData[input.name] = input.value;
            }
        });
        console.log('Form Data:', formData);
        alert('Form submitted! Check console for data.');
    };
    container.appendChild(submitBtn);
}

// Format label text (convert camelCase to Title Case)
function formatLabel(key) {
    return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

