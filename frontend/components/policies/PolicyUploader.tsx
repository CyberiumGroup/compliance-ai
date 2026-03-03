'use client';

import { useState } from 'react';
import { FileUpload, Input, Button, ErrorMessage } from '@/components/ui';
import { uploadPolicy } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { PolicyUploadResponse } from '@/lib/types';

interface PolicyUploaderProps {
  assessmentId: string;
  onUploadComplete: (response: PolicyUploadResponse) => void;
  documentType?: 'policy' | 'evidence';
}

export function PolicyUploader({ assessmentId, onUploadComplete, documentType = 'policy' }: PolicyUploaderProps) {
  const userId = useUserId();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState({
    name: '',
    description: '',
    version: '',
    owner: '',
  });

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    if (!metadata.name) {
      setMetadata({ ...metadata, name: file.name.replace(/\.[^/.]+$/, '') });
    }
  };

  const handleUpload = async () => {
    if (!userId || !selectedFile) return;

    setUploading(true);
    setError(null);

    try {
      const response = await uploadPolicy(assessmentId, selectedFile, { ...metadata, document_type: documentType }, userId);
      onUploadComplete(response);
      setSelectedFile(null);
      setMetadata({ name: '', description: '', version: '', owner: '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <FileUpload
        accept=".pdf,.docx,.doc,.txt,.md"
        onFileSelect={handleFileSelect}
        uploading={uploading}
        label={documentType === 'evidence' ? 'Upload Evidence Document' : 'Upload Policy Document'}
        helperText="PDF, DOCX, TXT, or Markdown files"
      />

      {selectedFile && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            Selected file: <span className="font-medium">{selectedFile.name}</span>
          </p>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Policy Name"
              value={metadata.name}
              onChange={(e) => setMetadata({ ...metadata, name: e.target.value })}
              placeholder="Information Security Policy"
            />
            <Input
              label="Version"
              value={metadata.version}
              onChange={(e) => setMetadata({ ...metadata, version: e.target.value })}
              placeholder="1.0"
            />
            <Input
              label="Owner"
              value={metadata.owner}
              onChange={(e) => setMetadata({ ...metadata, owner: e.target.value })}
              placeholder="Security Team"
            />
            <Input
              label="Description"
              value={metadata.description}
              onChange={(e) => setMetadata({ ...metadata, description: e.target.value })}
              placeholder="Brief description..."
            />
          </div>

          <div className="flex justify-end">
            <Button onClick={handleUpload} loading={uploading}>
              {documentType === 'evidence' ? 'Upload Evidence' : 'Upload Policy'}
            </Button>
          </div>
        </div>
      )}

      {error && <ErrorMessage message={error} />}
    </div>
  );
}
