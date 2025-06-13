"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react"
import { useSearchParams } from "next/navigation"
import { cn } from "@/lib/utils"

// Sample files data
const sampleFiles = [
  {
    id: 1,
    name: "2024_W2_Form.pdf",
    status: "processed",
    size: "1.2 MB",
    date: "May 19, 2025",
    recognizedFile: "W-2 Wage and Tax Statement",
  },
  {
    id: 2,
    name: "1099_Contractor.pdf",
    status: "processing",
    size: "0.8 MB",
    date: "May 19, 2025",
    recognizedFile: "",
  },
  {
    id: 3,
    name: "Business_Expenses_2024.xlsx",
    status: "processed",
    size: "2.4 MB",
    date: "May 19, 2025",
    recognizedFile: "Schedule C Expenses",
  },
  {
    id: 4,
    name: "Charitable_Donations.pdf",
    status: "error",
    size: "0.5 MB",
    date: "May 19, 2025",
    recognizedFile: "",
  },
  {
    id: 5,
    name: "Mortgage_Interest.pdf",
    status: "processed",
    size: "0.7 MB",
    date: "May 19, 2025",
    recognizedFile: "Form 1098 Mortgage Interest",
  },
]

export default function FilesPage() {
  // Get the search params once, outside of any effects
  const searchParamsString = useSearchParams().toString()
  const searchParams = new URLSearchParams(searchParamsString)
  const [files, setFiles] = useState(sampleFiles)
  const [isUsingSampleFiles, setIsUsingSampleFiles] = useState(false)
  const [newlyAddedFileIds, setNewlyAddedFileIds] = useState<number[]>([])

  useEffect(() => {
    // Use a function to determine the initial state to avoid multiple state updates
    const initializeFiles = () => {
      const source = searchParams.get("source")
      if (source === "sample") {
        setIsUsingSampleFiles(true)
        setFiles(sampleFiles)
      } else {
        try {
          // In a real app, we would fetch the user's uploaded files here
          // For now, we'll just use an empty array if no files were uploaded
          const uploadedFilesStr = localStorage.getItem("uploadedFiles")
          if (uploadedFilesStr) {
            const uploadedFiles = JSON.parse(uploadedFilesStr)
            if (uploadedFiles.length > 0) {
              setFiles(uploadedFiles)
              // Mark all files as newly added for animation
              setNewlyAddedFileIds(uploadedFiles.map((file: any) => file.id))
              // Clear the animation after 2 seconds
              setTimeout(() => {
                setNewlyAddedFileIds([])
              }, 2000)
            }
          }
        } catch (error) {
          console.error("Error parsing uploaded files:", error)
          // If there's an error, just use an empty array
          setFiles([])
        }
      }
    }

    // Only run this effect once on component mount
    initializeFiles()

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty dependency array means this only runs once on mount

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="bg-white rounded-xl shadow-sm p-6 transition-all duration-300 hover:shadow-md">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Your Files</h1>
            {isUsingSampleFiles && <p className="text-sm text-gray-500 mt-1">Viewing sample files for demonstration</p>}
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700 group" onClick={() => window.history.back()}>
            Upload More Files
            <span className="inline-block transition-transform duration-300 group-hover:translate-x-1 ml-1">→</span>
          </Button>
        </div>

        {files.length > 0 ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>File Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Upload Date</TableHead>
                  <TableHead>Recognised File</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {files.map((file) => (
                  <TableRow
                    key={file.id}
                    className={cn(
                      "transition-all duration-300 hover:bg-gray-50",
                      newlyAddedFileIds.includes(file.id) ? "animate-pulse bg-blue-50" : "",
                    )}
                  >
                    <TableCell className="font-medium">
                      <div className="flex items-center">
                        <FileText className="h-5 w-5 mr-2 text-blue-500" />
                        {file.name}
                      </div>
                    </TableCell>
                    <TableCell>
                      {file.status === "processed" && (
                        <div className="flex items-center text-green-600">
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Processed
                        </div>
                      )}
                      {file.status === "processing" && (
                        <div className="flex items-center text-amber-600">
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                          Processing
                        </div>
                      )}
                      {file.status === "error" && (
                        <div className="flex items-center text-red-600">
                          <AlertCircle className="h-4 w-4 mr-1" />
                          Error
                        </div>
                      )}
                    </TableCell>
                    <TableCell>{file.size}</TableCell>
                    <TableCell>{file.date}</TableCell>
                    <TableCell>{file.recognizedFile || "-"}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-blue-600 hover:text-blue-800 hover:bg-blue-50 transition-colors duration-200"
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No files found</h3>
            <p className="text-gray-500 mb-6">Upload some files to get started with Ctrl+Filing</p>
            <Button
              className="bg-blue-600 hover:bg-blue-700 transition-all duration-200 hover:translate-y-[-2px] hover:shadow-lg active:scale-[0.97] active:shadow-none"
              onClick={() => window.history.back()}
            >
              Upload Files
            </Button>
          </div>
        )}

        {files.length > 0 && (
          <div className="mt-8 p-4 bg-blue-50 rounded-lg transition-all duration-300 hover:bg-blue-100">
            <h2 className="text-lg font-medium text-gray-900 mb-2">AI Processing Complete</h2>
            <p className="text-gray-600">
              Our AI has analyzed your tax documents and identified potential deductions. View the full report to see
              how we can help optimize your tax filing.
            </p>
            <Button className="mt-4 bg-blue-600 hover:bg-blue-700 group">
              View Tax Report
              <span className="inline-block transition-transform duration-300 group-hover:translate-x-1 ml-1">→</span>
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
