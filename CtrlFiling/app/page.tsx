"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { useDropzone } from "react-dropzone"
import { Button } from "@/components/ui/button"
import { Toggle } from "@/components/ui/toggle"
import { cn } from "@/lib/utils"
import { Upload, FileText, AlertCircle, CheckCircle, BarChart3, Clock, Shield, ArrowRight } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { fileUploadAnimationClasses } from "@/lib/animation-utils"
import { CTASection } from "@/components/cta-section"

export default function Home() {
  const router = useRouter()
  const [uploadMethod, setUploadMethod] = useState<"batch" | "sample">("batch")
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError(null)
    if (acceptedFiles.length > 10) {
      setError("Maximum 10 files allowed")
      return
    }
    setFiles(acceptedFiles)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],
    },
    maxFiles: 10,
  })

  const handleUpload = () => {
    if (files.length === 0) {
      setError("Please select at least one file")
      return
    }

    // In a real application, you would upload the files to a server here
    // For this demo, we'll store them in localStorage and redirect
    localStorage.setItem(
      "uploadedFiles",
      JSON.stringify(
        files.map((file, index) => ({
          id: Date.now() + index,
          name: file.name,
          status: "processing",
          size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
          date: new Date().toLocaleDateString(),
          recognizedFile: "",
        })),
      ),
    )

    router.push("/files")
  }

  const handleToggleChange = (value: "batch" | "sample") => {
    setUploadMethod(value)
    setFiles([])
    setError(null)
  }

  const handleUseSampleFiles = () => {
    router.push("/files?source=sample")
  }

  return (
    <>
      {/* Hero Section */}
      <div className="bg-blue-600 text-white">
        <div className="container mx-auto px-4 py-12">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* File Upload Section */}
            <div className="order-2 md:order-1">
              <div className="bg-blue-50 rounded-xl p-6 shadow-sm">
                <div className="flex space-x-2 mb-6">
                  <Toggle
                    pressed={uploadMethod === "batch"}
                    onPressedChange={() => handleToggleChange("batch")}
                    className={cn(
                      "data-[state=on]:bg-blue-600 data-[state=on]:text-white",
                      "rounded-l-full rounded-r-none flex-1 justify-center",
                      "transition-all duration-200 ease-in-out",
                    )}
                  >
                    Batch Upload
                  </Toggle>
                  <Toggle
                    pressed={uploadMethod === "sample"}
                    onPressedChange={() => handleToggleChange("sample")}
                    className={cn(
                      "data-[state=on]:bg-blue-600 data-[state=on]:text-white",
                      "rounded-r-full rounded-l-none flex-1 justify-center",
                      "transition-all duration-200 ease-in-out",
                    )}
                  >
                    Use Sample Files
                  </Toggle>
                </div>

                {uploadMethod === "batch" ? (
                  <div
                    {...getRootProps()}
                    className={cn(
                      "border-2 border-dashed border-blue-300 rounded-lg p-8 text-center cursor-pointer",
                      fileUploadAnimationClasses.base,
                      isDragActive ? fileUploadAnimationClasses.dragActive : "hover:border-blue-500 hover:bg-blue-50",
                    )}
                  >
                    <input {...getInputProps()} />
                    <div className="flex flex-col items-center">
                      <Upload className="h-12 w-12 text-blue-500 mb-4" />
                      <p className="text-gray-700 mb-2">Click to browse or drag and drop your files</p>
                      <p className="text-sm text-gray-500">Max 10 files (.pdf, .xlsx, .xls, .csv)</p>
                    </div>
                  </div>
                ) : (
                  <div className="border-2 border-dashed border-blue-300 rounded-lg p-8 text-center">
                    <FileText className="h-12 w-12 text-blue-500 mx-auto mb-4" />
                    <p className="text-gray-700 mb-2">Use our sample tax files for demonstration</p>
                    <Button className="mt-4 bg-blue-600 hover:bg-blue-700" onClick={handleUseSampleFiles}>
                      Load Sample Files
                    </Button>
                  </div>
                )}

                {error && (
                  <Alert variant="destructive" className="mt-4">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {files.length > 0 && (
                  <div className="mt-6">
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      {files.length} {files.length === 1 ? "file" : "files"} selected
                    </p>
                    <ul className="space-y-2 max-h-32 overflow-y-auto">
                      {files.map((file, index) => (
                        <li key={index} className="text-sm text-gray-600 flex items-center">
                          <FileText className="h-4 w-4 mr-2 text-blue-500" />
                          {file.name}
                        </li>
                      ))}
                    </ul>
                    <Button className="w-full mt-4 bg-blue-600 hover:bg-blue-700" onClick={handleUpload}>
                      Upload Files
                    </Button>
                  </div>
                )}
              </div>
            </div>

            {/* Display Section */}
            <div className="order-1 md:order-2">
              <div className="text-center md:text-left mb-8 md:mb-0">
                <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4 animate-in fade-in slide-in-from-bottom-5 duration-700">
                  Supercharge Tax Preparation with AI
                </h1>
                <p className="text-xl md:text-2xl mb-6 animate-in fade-in slide-in-from-bottom-5 duration-700 delay-200">
                  Unsh*t Your Tax Season with Ctrl+Filing
                </p>
                <Image
                  src="/illustration.png"
                  alt="Tax Preparation Illustration"
                  width={500}
                  height={400}
                  className="mx-auto md:mx-0 animate-in fade-in slide-in-from-bottom-5 duration-700 delay-300"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Ctrl+Filing – Tax Tech With Actual Intelligence
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Empowering you to handle tax season with greater speed, accuracy, and confidence - with our suite of AI
              Agents.
            </p>
          </div>

          {/* TaxPrep Bot Feature */}
          <div className="max-w-6xl mx-auto mb-24">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div className="group">
                <Image
                  src="/taxprep-bot.png"
                  alt="TaxPrep Bot Illustration"
                  width={400}
                  height={400}
                  className="mx-auto transition-transform duration-500 ease-in-out group-hover:scale-105"
                />
              </div>
              <div>
                <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">TaxPrep Bot</h3>
                <p className="text-xl text-gray-600 mb-4">"AI that prepares in CCH Axcess & Lacerte"</p>
                <p className="text-gray-600 mb-4">
                  Export directly to tax software like <strong>CCH Axcess & Lacerte</strong>, extract data with AI,
                  validate inputs with smart checks, and get client-ready returns in minutes{" "}
                  <strong>—cutting prep time by up to 80%</strong>.
                </p>
                <Button className="bg-green-600 hover:bg-green-700 group">
                  Learn More{" "}
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                </Button>
              </div>
            </div>
          </div>

          {/* Reconciliation Wizard Feature */}
          <div className="max-w-6xl mx-auto mb-24">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div className="order-2 md:order-1">
                <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Reconciliation Wizard</h3>
                <p className="text-xl text-gray-600 mb-4">"Magically matches. No wand required."</p>
                <p className="text-gray-600 mb-4">
                  Automatically generate formatted <strong>reconciliation sheets</strong>, spot key year-over-year
                  changes, tie schedules to returns with precision, and request custom templates{" "}
                  <strong>tailored to your firm's workflows</strong>—all in one place.
                </p>
                <Button className="bg-red-500 hover:bg-red-600 group">
                  Learn More{" "}
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                </Button>
              </div>
              <div className="order-1 md:order-2 group">
                <Image
                  src="/reconciliation-wizard.png"
                  alt="Reconciliation Wizard Illustration"
                  width={400}
                  height={400}
                  className="mx-auto transition-transform duration-500 ease-in-out group-hover:scale-105"
                />
              </div>
            </div>
          </div>

          {/* Tic Tie Slayer Feature */}
          <div className="max-w-6xl mx-auto">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div className="group">
                <Image
                  src="/tic-tie-slayer.png"
                  alt="Tic Tie Slayer Illustration"
                  width={400}
                  height={400}
                  className="mx-auto transition-transform duration-500 ease-in-out group-hover:scale-105"
                />
              </div>
              <div>
                <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Tic Tie Slayer</h3>
                <p className="text-xl text-gray-600 mb-4">"Destroying busywork, one tie at a time."</p>
                <p className="text-gray-600 mb-4">
                  Easily navigate tax files with <strong>auto-generated bookmarks</strong>, verify all calculations
                  instantly, generate <strong>compliant audit-ready workpapers</strong>, & link source documents to
                  final returns with <strong>audit trails — all fully automated</strong>.
                </p>
                <Button className="bg-amber-500 hover:bg-amber-600 group">
                  Learn More{" "}
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Roadmap Section */}
      <div className="bg-gray-900 text-white py-16">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-bold mb-4 text-center animate-in fade-in-50 duration-700">Roadmap</h2>
            <p className="text-xl text-gray-400 mb-16 text-center animate-in fade-in-50 duration-700 delay-100">
              This roadmap outlines our goals and where we want to take Ctrl+Filing.
            </p>

            <div className="relative">
              {/* Vertical line */}
              <div className="absolute left-4 md:left-8 top-0 bottom-0 w-0.5 bg-gray-700"></div>

              {/* Roadmap items */}
              <div className="space-y-16">
                {/* Item 1 */}
                <div className="relative pl-12 md:pl-20 animate-in fade-in-50 slide-in-from-left-5 duration-700">
                  <div className="absolute left-0 top-1 h-8 w-8 rounded-full bg-blue-500 border-4 border-gray-800 z-10 flex items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-white"></div>
                  </div>
                  <div className="flex flex-col md:flex-row md:items-center justify-between">
                    <div>
                      <h3 className="text-2xl font-bold mb-2">Planning & Pre-Production</h3>
                      <p className="text-gray-400 mb-4">
                        Quality comes first. We took our time to plan out everything and build our production pipeline.
                      </p>
                    </div>
                    <div className="text-gray-500 md:ml-8">1. Sept</div>
                  </div>
                </div>

                {/* Item 2 */}
                <div className="relative pl-12 md:pl-20 animate-in fade-in-50 slide-in-from-left-5 duration-700 delay-100">
                  <div className="absolute left-0 top-1 h-8 w-8 rounded-full bg-blue-500 border-4 border-gray-800 z-10 flex items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-white"></div>
                  </div>
                  <div className="flex flex-col md:flex-row md:items-center justify-between">
                    <div>
                      <h3 className="text-2xl font-bold mb-2">Production</h3>
                      <p className="text-gray-400 mb-4">
                        Starting the production on the AI models and integrations with tax software platforms.
                      </p>
                    </div>
                    <div className="text-gray-500 md:ml-8">1. Oct</div>
                  </div>
                </div>

                {/* Item 3 */}
                <div className="relative pl-12 md:pl-20 animate-in fade-in-50 slide-in-from-left-5 duration-700 delay-200">
                  <div className="absolute left-0 top-1 h-8 w-8 rounded-full bg-blue-500 border-4 border-gray-800 z-10 flex items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-white"></div>
                  </div>
                  <div className="flex flex-col md:flex-row md:items-center justify-between">
                    <div>
                      <h3 className="text-2xl font-bold mb-2">Beta Launch</h3>
                      <p className="text-gray-400 mb-4">
                        Our most active community members will be able to join the beta testing program.
                      </p>
                    </div>
                    <div className="text-gray-500 md:ml-8">End of Nov</div>
                  </div>
                </div>

                {/* Item 4 */}
                <div className="relative pl-12 md:pl-20 animate-in fade-in-50 slide-in-from-left-5 duration-700 delay-300">
                  <div className="absolute left-0 top-1 h-8 w-8 rounded-full bg-gray-700 border-4 border-gray-800 z-10 flex items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-white"></div>
                  </div>
                  <div className="flex flex-col md:flex-row md:items-center justify-between">
                    <div>
                      <h3 className="text-2xl font-bold mb-2">Public Launch</h3>
                      <p className="text-gray-400 mb-4">
                        Full public launch with all features available to subscribers. Special pricing for early
                        adopters.
                      </p>
                    </div>
                    <div className="text-gray-500 md:ml-8">TBA</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Hero Feature Section */}
      <div className="bg-gray-100 py-16">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="animate-in fade-in-50 slide-in-from-left-5 duration-700">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Simplify your tax filing process</h2>
              <p className="text-lg text-gray-600 mb-6">
                Our AI-powered platform automatically identifies and categorizes tax documents, extracts relevant
                information, and helps you maximize deductions.
              </p>
              <div className="flex flex-col space-y-4">
                <div className="flex items-start group">
                  <div className="flex-shrink-0 mt-1 transition-transform duration-300 group-hover:scale-110">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-gray-900">Automatic Document Recognition</h3>
                    <p className="text-gray-600">Our AI identifies W-2s, 1099s, and other tax forms automatically</p>
                  </div>
                </div>
                <div className="flex items-start group">
                  <div className="flex-shrink-0 mt-1 transition-transform duration-300 group-hover:scale-110">
                    <Clock className="h-5 w-5 text-green-500" />
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-gray-900">Save Hours of Manual Work</h3>
                    <p className="text-gray-600">Reduce tax preparation time by up to 80% with our automated system</p>
                  </div>
                </div>
                <div className="flex items-start group">
                  <div className="flex-shrink-0 mt-1 transition-transform duration-300 group-hover:scale-110">
                    <Shield className="h-5 w-5 text-green-500" />
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-gray-900">Secure and Compliant</h3>
                    <p className="text-gray-600">Bank-level encryption and compliance with tax regulations</p>
                  </div>
                </div>
              </div>
              <div className="mt-8 flex items-center">
                <div className="flex -space-x-2 mr-4">
                  <div className="w-8 h-8 rounded-full bg-blue-200 flex items-center justify-center text-xs text-blue-600 border-2 border-white">
                    JD
                  </div>
                  <div className="w-8 h-8 rounded-full bg-green-200 flex items-center justify-center text-xs text-green-600 border-2 border-white">
                    KL
                  </div>
                  <div className="w-8 h-8 rounded-full bg-purple-200 flex items-center justify-center text-xs text-purple-600 border-2 border-white">
                    MN
                  </div>
                </div>
                <span className="text-sm text-gray-600">5,000+ tax professionals trust Ctrl+Filing</span>
              </div>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-lg transition-all duration-300 hover:shadow-xl hover:translate-y-[-4px] animate-in fade-in-50 slide-in-from-right-5 duration-700">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-gray-900">Tax Savings Dashboard</h3>
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
              <div className="space-y-4">
                <div className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors duration-200">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">Business Expenses</span>
                    <span className="text-green-600 font-medium">$4,250</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full animate-in slide-in-from-left duration-1000"
                      style={{ width: "75%" }}
                    ></div>
                  </div>
                </div>
                <div className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors duration-200">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">Charitable Donations</span>
                    <span className="text-green-600 font-medium">$1,800</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full animate-in slide-in-from-left duration-1000 delay-200"
                      style={{ width: "40%" }}
                    ></div>
                  </div>
                </div>
                <div className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors duration-200">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">Home Office Deduction</span>
                    <span className="text-green-600 font-medium">$2,100</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full animate-in slide-in-from-left duration-1000 delay-400"
                      style={{ width: "55%" }}
                    ></div>
                  </div>
                </div>
              </div>
              <div className="mt-6 pt-4 border-t border-gray-200">
                <div className="flex justify-between items-center">
                  <span className="text-lg font-bold">Potential Tax Savings</span>
                  <span className="text-xl font-bold text-green-600">$2,430</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <CTASection />
    </>
  )
}
